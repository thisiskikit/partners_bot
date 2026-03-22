#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
insta_download.py (429 최소화 + 이메일 발송)

동작 요약
- 시트: '영상다운로드'
- 대상 행:
  - '인스타업로드링크' 값이 있고
  - '인스타다운로드' == '작업 시작'
- 저장 경로:
  - '작업일자' (예: 12/26, 12/18 등 MM/DD)를 읽어
  - YYYY-MM-DD/insta_download/ 로 저장
  - 파일명: insta_<다운로드파일명>.mp4 (+ 썸네일 jpg)
- 메일:
  - 제목: [2차 insta] <다운로드파일명>
  - 본문에 아래를 포함:
    - 인포크넘버
    - 추가업로드멘트
    - 쿠팡파트너스링크
    - 인스타 원본 링크
  - 수신자 우선순위: 시트 '수신이메일' → .env EMAIL_TO → SMTP USER
- SMTP 설정: 시트 B11~B14 (B11=HOST, B12=PORT, B13=USER, B14=PASS)
- 읽기: 필요한 열만 batch_get로 최소화
- 쓰기: batch_update로 모아서 최소 횟수로 반영
"""

import os
import re
import json
import time
import random
import datetime
from datetime import date
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from yt_dlp import YoutubeDL

import mimetypes
import smtplib
from email.message import EmailMessage

# ───────────────── 설정 ─────────────────
DEFAULT_HEADER_ROW = 4              # 기본 헤더 행(다를 수 있어 fallback 자동탐지)
SHEET_NAME = os.getenv("SHEET_TAB", "영상다운로드").strip()
WRITE_BATCH_CHUNK = 400
PER_DOWNLOAD_SLEEP = (0.8, 1.6)

# ───────────────── 환경 ─────────────────
load_dotenv(dotenv_path=".env")

SPREADSHEET_LINK = (os.getenv("SPREADSHEET_LINK_inpock") or "").strip()
CREDS_VALUE      = (os.getenv("CREDS_FILE_INPOCK") or "").strip()   # 파일 경로 or JSON 문자열
EMAIL_TO_DEFAULT = (os.getenv("EMAIL_TO") or "").strip()            # 선택: 콤마 구분

if not SPREADSHEET_LINK or not CREDS_VALUE:
    raise RuntimeError("환경변수 SPREADSHEET_LINK_inpock / CREDS_FILE_INPOCK 를 .env에 설정하세요.")

# ───────────────── 공용 유틸 ─────────────────
def safe_name(s: str, max_len: int = 150) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "_", s or "")
    s = s.strip()
    return s[:max_len] or "file"

def resolve_creds(creds_value: str) -> str:
    """서비스계정 값이 경로면 그대로, JSON 문자열이면 임시파일로 저장 후 그 경로 반환"""
    p = Path(creds_value)
    if p.exists():
        return str(p.resolve())
    try:
        data = json.loads(creds_value)
        tmp = Path.cwd() / ".sa_tmp_insta.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(tmp.resolve())
    except Exception:
        raise RuntimeError(
            "CREDS_FILE_INPOCK 값이 유효한 파일 경로도, 올바른 JSON 문자열도 아닙니다. "
            "서비스 계정 파일 경로를 넣거나 JSON 내용을 그대로 넣어 주세요."
        )

def col_letter(col: int) -> str:
    s = ""
    while col:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s

def backoff_sleep(attempt: int, base: float = 1.0, jitter: float = 0.4, min_s: float = 0.2, max_s: float = 60.0) -> None:
    t = base * (2 ** (attempt - 1))
    t = t * (1 + random.uniform(-jitter, jitter))
    time.sleep(min(max_s, max(min_s, t)))

def is_rate_limit_err(e: Exception) -> bool:
    s = str(e).lower()
    return ("429" in s) or ("too many requests" in s) or ("rate limit" in s)

def batch_get_with_backoff(ws, ranges: List[str], max_attempts: int = 6):
    attempt = 1
    while True:
        try:
            return ws.batch_get(ranges, value_render_option="UNFORMATTED_VALUE")
        except (HttpError, Exception) as e:
            if attempt >= max_attempts or not is_rate_limit_err(e):
                raise
            print(f"[429] batch_get 재시도 {attempt}/{max_attempts}…")
            backoff_sleep(attempt, base=1.2)
            attempt += 1

def batch_update_with_backoff(ws, requests: List[Dict], max_attempts: int = 6) -> None:
    if not requests:
        return
    attempt = 1
    while True:
        try:
            ws.batch_update(requests)
            return
        except (HttpError, Exception) as e:
            if attempt >= max_attempts or not is_rate_limit_err(e):
                raise
            print(f"[429] batch_update 재시도 {attempt}/{max_attempts}…")
            backoff_sleep(attempt, base=1.2)
            attempt += 1

def workdate_to_folder(work_date_str: str) -> str:
    """
    작업일자: 'MM/DD' 또는 'M/D' (예: '12/26') 를 'YYYY-MM-DD'로 변환.
    - 연도 없으면 기본은 현재연도
    - 연말/연초 경계에서 ±180일 범위로 가장 자연스러운 연도 선택
    """
    s = (work_date_str or "").strip()
    today = date.today()

    if not s:
        return today.strftime("%Y-%m-%d")

    # YYYY-MM-DD / YYYY/MM/DD
    m = re.match(r"^\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s*$", s)
    if m:
        y, mo, d = map(int, m.groups())
        return date(y, mo, d).strftime("%Y-%m-%d")

    # MM/DD
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})\s*$", s)
    if m:
        mo, d = map(int, m.groups())
        candidates = []
        for y in (today.year - 1, today.year, today.year + 1):
            try:
                candidates.append(date(y, mo, d))
            except ValueError:
                pass
        if not candidates:
            return today.strftime("%Y-%m-%d")

        best = min(candidates, key=lambda dt: abs((dt - today).days))
        if abs((best - today).days) > 180:
            return today.strftime("%Y-%m-%d")
        return best.strftime("%Y-%m-%d")

    return today.strftime("%Y-%m-%d")

# ───────────────── 시트 연결 ─────────────────
CREDS_PATH = resolve_creds(CREDS_VALUE)

creds = Credentials.from_service_account_file(
    CREDS_PATH,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ],
)
gc = gspread.authorize(creds)
ws = gc.open_by_url(SPREADSHEET_LINK).worksheet(SHEET_NAME)

# ───────────────── 헤더 처리 ─────────────────
REQUIRED_HEADERS = [
    "인스타업로드링크",
    "인스타다운로드",
    "다운로드파일명",      # 비어도 자동 생성하지만 컬럼은 필요
    "작업일자",            # 저장폴더에 필요
]

def detect_header_row(ws, default_row: int, required: List[str], scan_rows: int = 50) -> int:
    """
    default_row에 required가 없으면 1~scan_rows 중 required 포함이 가장 많은 행을 헤더로 판정
    """
    row = [str(x).strip() for x in ws.row_values(default_row)]
    if all(h in row for h in required):
        return default_row

    best_row = None
    best_score = -1
    for r in range(1, scan_rows + 1):
        row_r = [str(x).strip() for x in ws.row_values(r)]
        if not row_r:
            continue
        score = sum(1 for h in required if h in row_r)
        if score > best_score:
            best_score = score
            best_row = r
        if score == len(required):
            return r

    if best_row is None or best_score <= 0:
        raise RuntimeError(f"헤더 행을 찾지 못했습니다. required={required}")
    return best_row

HEADER_ROW = detect_header_row(ws, DEFAULT_HEADER_ROW, REQUIRED_HEADERS, scan_rows=60)
header: List[str] = ws.row_values(HEADER_ROW)

def col_idx(name: str) -> int:
    if name not in header:
        raise RuntimeError(f"[에러] 헤더({HEADER_ROW}행)에 '{name}' 컬럼이 없습니다.")
    return header.index(name) + 1

# ───────────────── 컬럼 인덱스 ─────────────────
IDX: Dict[str, Optional[int]] = {
    "인스타업로드링크": col_idx("인스타업로드링크"),
    "인스타다운로드":   col_idx("인스타다운로드"),
    "다운로드파일명":   col_idx("다운로드파일명"),
    "작업일자":         col_idx("작업일자"),
}

# 선택/비고/옵션 열: 존재 시 사용
IDX["작업 완료시간"]   = col_idx("작업 완료시간")   if "작업 완료시간" in header else None
IDX["작업 비고"]       = col_idx("작업 비고")       if "작업 비고" in header else None
IDX["작업 선택"]       = col_idx("작업 선택")       if "작업 선택" in header else None
IDX["수신이메일"]      = col_idx("수신이메일")      if "수신이메일" in header else None

# ✅ 메일 본문에 추가할 컬럼들
IDX["인포크넘버"]       = col_idx("인포크넘버")       if "인포크넘버" in header else None
IDX["추가업로드멘트"]   = col_idx("추가업로드멘트")   if "추가업로드멘트" in header else None
IDX["쿠팡파트너스링크"] = col_idx("쿠팡파트너스링크") if "쿠팡파트너스링크" in header else None

# (선택) 자동 파일명 생성에 쓰면 유용한 컬럼
IDX["키워드"] = col_idx("키워드") if "키워드" in header else None

# ───────────────── 시트 읽기 ─────────────────
def read_needed_columns(start_row: int) -> Tuple[int, Dict[str, List[str]]]:
    """
    필요한 컬럼만 batch_get 1회로 읽음.
    dict 순서/zip 꼬임 방지를 위해 keys_order를 ranges와 동일하게 구성.
    """
    keys_order: List[str] = []
    ranges: List[str] = []
    for key, c in IDX.items():
        if c is None:
            continue
        keys_order.append(key)
        col = col_letter(c)
        ranges.append(f"{col}{start_row}:{col}")

    values_list = batch_get_with_backoff(ws, ranges)
    max_len = max((len(col_vals) for col_vals in values_list), default=0)

    col_to_vals: Dict[str, List[str]] = {}
    for k, col_vals in zip(keys_order, values_list):
        padded = col_vals + [[""]] * (max_len - len(col_vals))
        col_to_vals[k] = [row[0] if row else "" for row in padded]
    return max_len, col_to_vals

# ───────────────── SMTP 설정 ─────────────────
def read_smtp_cfg(ws) -> Dict[str, str]:
    # B11~B14를 batch_get로 1회에 읽기
    res = batch_get_with_backoff(ws, ["B11:B14"])
    cells = (res[0] if res else [])
    # cells = [[val],[val],...]
    host = (cells[0][0] if len(cells) > 0 and cells[0] else "").strip()
    port = (cells[1][0] if len(cells) > 1 and cells[1] else "").strip()
    user = (cells[2][0] if len(cells) > 2 and cells[2] else "").strip()
    pwd  = (cells[3][0] if len(cells) > 3 and cells[3] else "").strip()

    if not (host and user and pwd):
        raise RuntimeError("SMTP 설정(B11~B14) 중 일부가 비어 있습니다. (B11=HOST, B12=PORT, B13=USER, B14=PASS)")

    try:
        port_i = int(port) if port else 587
    except ValueError:
        port_i = 587

    return {"host": host, "port": port_i, "user": user, "pass": pwd}

# ───────────────── 다운로드/첨부 ─────────────────
def download_instagram(ig_url: str, out_dir: Path, basename: str) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / (basename + ".%(ext)s"))

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "writethumbnail": True,
        "postprocessors": [
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
        ],
        # 요청 간격(429 완화)
        "sleep_interval_requests": 1.0,
        "max_sleep_interval_requests": 2.0,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([ig_url])
        return True
    except Exception as e:
        print(f"[Error] 인스타 다운로드 실패: {ig_url} / {e}")
        return False

def find_just_downloaded_files(out_dir: Path, basename: str) -> List[Path]:
    attachments: List[Path] = []
    jpg = out_dir / f"{basename}.jpg"
    if jpg.exists():
        attachments.append(jpg)

    for ext in (".mp4", ".mov", ".m4v", ".webm", ".mkv"):
        p = out_dir / f"{basename}{ext}"
        if p.exists():
            attachments.append(p)
            break
    return attachments

def send_email_quick(subject: str, body: str, to_list: List[str], attachments: List[Path], smtp_cfg: Dict[str, str]) -> None:
    msg = EmailMessage()
    sender = smtp_cfg["user"]
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    msg.set_content(body)

    for p in attachments:
        try:
            mime, _ = mimetypes.guess_type(str(p))
            maintype, subtype = (mime.split("/", 1) if mime else ("application", "octet-stream"))
            with open(p, "rb") as f:
                msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=p.name)
        except Exception as e:
            print(f"[첨부 실패] {p} / {e}")

    with smtplib.SMTP(smtp_cfg["host"], int(smtp_cfg["port"]), timeout=60) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_cfg["user"], smtp_cfg["pass"])
        server.send_message(msg)

# ───────────────── 메인 ─────────────────
def main():
    data_start = HEADER_ROW + 1

    total_rows, cols = read_needed_columns(start_row=data_start)
    n = total_rows

    # 열 리스트
    links     = cols.get("인스타업로드링크", [])
    states    = cols.get("인스타다운로드", [])
    names     = cols.get("다운로드파일명", [])
    workdates = cols.get("작업일자", [])

    recvcol   = cols.get("수신이메일", []) if IDX.get("수신이메일") else []
    inpockcol = cols.get("인포크넘버", []) if IDX.get("인포크넘버") else []
    mentcol   = cols.get("추가업로드멘트", []) if IDX.get("추가업로드멘트") else []
    cpcol     = cols.get("쿠팡파트너스링크", []) if IDX.get("쿠팡파트너스링크") else []
    kwcol     = cols.get("키워드", []) if IDX.get("키워드") else []

    notes_col_exists  = IDX.get("작업 비고") is not None
    choice_col_exists = IDX.get("작업 선택") is not None

    smtp_cfg = read_smtp_cfg(ws)

    processed = 0
    write_requests: List[Dict] = []

    for i in range(n):
        rownum = data_start + i
        try:
            link_val  = str(links[i] if i < len(links) else "").strip()
            state_val = str(states[i] if i < len(states) else "").strip()
            dl_name   = str(names[i] if i < len(names) else "").strip()

            # ✅ '작업 시작'만 처리
            if not link_val or state_val != "작업 시작":
                continue

            # 작업일자 기반 폴더
            work_date = str(workdates[i] if i < len(workdates) else "").strip()
            folder_date = workdate_to_folder(work_date)
            target_dir = Path(folder_date) / "insta_download"

            # 다운로드파일명 비어있으면 자동 생성(인포크넘버/키워드/행번호)
            inpock_no = str(inpockcol[i] if i < len(inpockcol) else "").strip()
            keyword   = str(kwcol[i] if i < len(kwcol) else "").strip()

            if not dl_name:
                dl_name = inpock_no or keyword or f"row{rownum}"
                dl_name = safe_name(dl_name)

                # 시트에 다운로드파일명 채워넣기
                write_requests.append({
                    "range": gspread.utils.rowcol_to_a1(rownum, IDX["다운로드파일명"]),
                    "values": [[dl_name]],
                })

            basename = safe_name(f"insta_{dl_name}")
            print(f"[insta] row={rownum} 작업일자={work_date} → {folder_date} / name={dl_name}")

            ok = download_instagram(link_val, target_dir, basename)

            if ok:
                attachments = find_just_downloaded_files(target_dir, basename)

                # 수신자 결정
                recv_val = str(recvcol[i] if i < len(recvcol) else "").strip()
                if recv_val:
                    to_list = [x.strip() for x in recv_val.split(",") if x.strip()]
                elif EMAIL_TO_DEFAULT:
                    to_list = [x.strip() for x in EMAIL_TO_DEFAULT.split(",") if x.strip()]
                else:
                    to_list = [smtp_cfg["user"]]

                # 본문 구성(요청하신 3개 컬럼 포함)
                up_ment = str(mentcol[i] if i < len(mentcol) else "").strip()
                cp_link = str(cpcol[i] if i < len(cpcol) else "").strip()

                subject = f"[2차 insta] {dl_name}"

                body_lines = []
                body_lines.append("다운로드 완료 안내드립니다.")
                body_lines.append("")
                body_lines.append("■ 작업 정보")
                if inpock_no:
                    body_lines.append(f"- 인포크넘버: {inpock_no}")
                body_lines.append(f"- 작업일자: {work_date or '(빈값)'}")
                body_lines.append(f"- 저장폴더: {folder_date}/insta_download")
                body_lines.append(f"- 다운로드파일명: {dl_name}")
                body_lines.append("")

                if up_ment:
                    body_lines.append("■ 추가업로드멘트")
                    body_lines.append(up_ment)
                    body_lines.append("")

                if cp_link:
                    body_lines.append("■ 쿠팡파트너스링크")
                    body_lines.append(cp_link)
                    body_lines.append("")

                body_lines.append("■ 인스타 원본 링크")
                body_lines.append(link_val)
                body_lines.append("")
                body_lines.append("첨부된 영상/썸네일 확인 후, 후속 업로드 작업을 진행해 주세요.")

                body = "\n".join(body_lines)

                try:
                    send_email_quick(subject, body, to_list, attachments, smtp_cfg)
                except Exception as e:
                    note = f"[단계] 인스타다운로드\n[메일에러] {type(e).__name__}: {e}"
                    if notes_col_exists:
                        write_requests.append({
                            "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 비고"]),
                            "values": [[note]],
                        })
                    if choice_col_exists:
                        write_requests.append({
                            "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 선택"]),
                            "values": [["작업 중 에러"]],
                        })
                    # 다운로드는 성공했으므로 상태 완료(선택)
                    write_requests.append({
                        "range": gspread.utils.rowcol_to_a1(rownum, IDX["인스타다운로드"]),
                        "values": [["작업 완료"]],
                    })
                else:
                    # 메일까지 성공
                    write_requests.append({
                        "range": gspread.utils.rowcol_to_a1(rownum, IDX["인스타다운로드"]),
                        "values": [["작업 완료"]],
                    })
                    processed += 1

            else:
                note = f"[단계] 인스타다운로드\n[에러] 다운로드 실패\n[링크] {link_val}"
                if notes_col_exists:
                    write_requests.append({
                        "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 비고"]),
                        "values": [[note]],
                    })
                if choice_col_exists:
                    write_requests.append({
                        "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 선택"]),
                        "values": [["작업 중 에러"]],
                    })

            time.sleep(random.uniform(*PER_DOWNLOAD_SLEEP))

            if len(write_requests) >= WRITE_BATCH_CHUNK:
                batch_update_with_backoff(ws, write_requests)
                write_requests.clear()

        except Exception as e:
            note = f"[단계] 인스타다운로드\n[에러] {type(e).__name__}: {e}"
            if notes_col_exists:
                write_requests.append({
                    "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 비고"]),
                    "values": [[note]],
                })
            if choice_col_exists:
                write_requests.append({
                    "range": gspread.utils.rowcol_to_a1(rownum, IDX["작업 선택"]),
                    "values": [["작업 중 에러"]],
                })
            if len(write_requests) >= WRITE_BATCH_CHUNK:
                batch_update_with_backoff(ws, write_requests)
                write_requests.clear()

    if write_requests:
        batch_update_with_backoff(ws, write_requests)

    print(f"✅ 처리 완료. 다운로드+메일 성공 행 수: {processed}")

if __name__ == "__main__":
    main()
