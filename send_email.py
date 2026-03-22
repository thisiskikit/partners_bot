#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
send_email.py
- 시트(.env의 SPREADSHEET_LINK) '영상다운로드'에서
  '작업 선택' == '이메일발송' 인 행만 메일 발송
- SMTP 설정: 시트 B11(B11=HOST), B12(PORT), B13(USER), B14(PASS)
- 제목: '다운로드파일명'
- 본문: '쿠팡파트너스링크' '영상길이' '스크립트' '인스타글내용' '간소화멘트' '틱톡멘트'를 자연스럽게 구성
- 첨부: done/**/fin/fin_<다운로드파일명>, done/**/org/org_<다운로드파일명> 자동 탐색하여 첨부
- 수신자: .env EMAIL_TO (여러 명은 콤마 구분) → 시트 '수신이메일' 열(있으면 우선 적용) → 기본 smtp_user
"""
from smtplib import SMTPServerDisconnected  # ← 이미 있음

import os, sys, re, json, time, mimetypes, shutil, subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
from dotenv import load_dotenv

from email.message import EmailMessage
import smtplib
import ssl  # ✅ 이거 추가

# ─────────────────────────────────────────
# 환경 (SMTP_*는 사용 안 함)
# ─────────────────────────────────────────
load_dotenv(dotenv_path=".env")

SPREADSHEET_LINK = os.getenv("SPREADSHEET_LINK", "")
CREDS_FILE       = os.getenv("CREDS_FILE_OHL1", "")
EMAIL_TO_DEFAULT = os.getenv("EMAIL_TO", "")  # 콤마 구분 (선택)
TARGET_SHEET_NAME = os.getenv("TARGET_SHEET_NAME", "영상다운로드")
HEADER_ROW        = int(os.getenv("HEADER_ROW", "4"))
LOG_LEVEL         = os.getenv("LOG_LEVEL", "INFO").upper()

if not (SPREADSHEET_LINK and CREDS_FILE):
    raise RuntimeError("필수 환경변수 누락: SPREADSHEET_LINK, CREDS_FILE_OHL1 확인")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT_RAW = os.getenv("SMTP_PORT", "587").strip()
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()

try:
    SMTP_PORT = int(SMTP_PORT_RAW) if SMTP_PORT_RAW else 587
except ValueError:
    SMTP_PORT = 587

if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
    raise RuntimeError("SMTP_HOST / SMTP_USER / SMTP_PASS 환경변수가 비어 있습니다. .env 설정을 확인하세요.")

# ─────────────────────────────────────────
# 공용
# ─────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    levels = ["DEBUG","INFO","WARNING","ERROR"]
    if levels.index(level) >= levels.index(LOG_LEVEL):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {level} | {msg}")

def find_ffprobe() -> Optional[str]:
    env_path = os.getenv("FFPROBE_PATH")
    if env_path and Path(env_path).is_file():
        return env_path
    local = Path(__file__).resolve().parent / "data" / "ffprobe.exe"
    if local.is_file():
        return str(local)
    which = shutil.which("ffprobe")
    return which

def get_media_duration_seconds(path: Path) -> Optional[float]:
    ffprobe = find_ffprobe()
    if not ffprobe or not path or not path.exists():
        return None
    try:
        cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        j = json.loads(res.stdout)
        return float(j["format"]["duration"])
    except Exception as e:
        log(f"ffprobe 실패: {e}", "WARNING")
        return None

def sec_to_hms(sec: float) -> str:
    if sec is None:
        return ""
    s = int(round(sec))
    h = s // 3600
    m = (s % 3600) // 60
    s = s % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def sanitize_name(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[\r\n]+"," ", name or "")
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return (name.strip() or "file")[:max_len]

def safe_batch_update(ws, requests: List[Dict], max_attempts: int = 6):
    """429/5xx 대비 지수 백오프"""
    if not requests:
        return
    base = 1.4
    for attempt in range(1, max_attempts + 1):
        try:
            ws.batch_update(requests)
            return
        except APIError as e:
            msg = str(e)
            transient = any(code in msg for code in ("429","500","502","503","504"))
            if transient and attempt < max_attempts:
                sleep_s = min(20.0, base ** (attempt - 1))  # 1,1.4,1.96,…
                time.sleep(sleep_s)
                continue
            raise

# ─────────────────────────────────────────
# 첨부 파일 탐색
# ─────────────────────────────────────────
def find_attachments(done_root: Path, raw_filename: str) -> Tuple[Optional[Path], Optional[Path]]:
    """
    returns: (fin_path, org_path)
    """
    target_fin = f"fin_{raw_filename}"
    target_org = f"org_{raw_filename}"

    if not done_root.exists():
        return (None, None)

    dated_dirs = [p for p in done_root.iterdir() if p.is_dir()]
    dated_dirs.sort(key=lambda p: p.name, reverse=True)  # 최신 날짜 우선

    fin_path = None
    org_path = None
    for d in dated_dirs:
        fp = d / "fin" / target_fin
        op = d / "org" / target_org
        if fp.exists() and fin_path is None:
            fin_path = fp
        if op.exists() and org_path is None:
            org_path = op
        if fin_path and org_path:
            break
    return (fin_path, org_path)

# ─────────────────────────────────────────
# 본문 생성
# ─────────────────────────────────────────
def build_body(rowdata: Dict[str,str]) -> str:
    link   = rowdata.get("쿠팡파트너스링크","").strip()
    vlen   = rowdata.get("영상길이","").strip()
    script = rowdata.get("스크립트","").strip()
    insta  = rowdata.get("인스타글내용","").strip()
    simple = rowdata.get("간소화멘트","").strip()
    tiktok = rowdata.get("틱톡멘트","").strip()

    parts = []
    if link:
        parts.append(f"■ 링크\n{link}\n")
    if vlen:
        parts.append(f"■ 영상길이\n{vlen}\n")
    if script:
        parts.append(f"■ 나레이션 스크립트\n{script}\n")
    if insta:
        parts.append(f"■ 인스타그램 게시 문구(초안)\n{insta}\n")
    if simple:
        parts.append(f"■ 간소화 멘트\n{simple}\n")
    if tiktok:
        parts.append(f"■ 틱톡 게시 멘트(초안)\n{tiktok}\n")

    if not parts:
        parts.append("첨부 영상 관련 상세 내용은 시트를 참고해 주세요.\n")

    parts.append("\n감사합니다.")
    return "\n".join(parts)

# ─────────────────────────────────────────
# 이메일 전송 (시트에서 읽은 SMTP 설정 사용)
# ─────────────────────────────────────────
def _send_email_once(
    subject: str,
    body: str,
    to_addrs: List[str],
    attachments: List[Path],
    smtp: Dict[str, Any],
    sender_name: Optional[str] = None
):
    smtp_host = smtp["host"]
    smtp_port = int(smtp["port"])
    smtp_user = smtp["user"]
    smtp_pass = smtp["pass"]

    msg = EmailMessage()
    sender_display = f"{sender_name} <{smtp_user}>" if sender_name else smtp_user
    msg["From"] = sender_display
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body)

    # 첨부 파일
    for p in attachments:
        try:
            mime, _ = mimetypes.guess_type(str(p))
            maintype, subtype = (mime.split("/", 1) if mime else ("application", "octet-stream"))
            with open(p, "rb") as f:
                data = f.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)
        except Exception as e:
            log(f"첨부 실패({p}): {repr(e)}", "WARNING")

    # 포트에 따라 SSL / STARTTLS 분기
    if smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=300) as server:
            # 필요시 디버깅
            # server.set_debuglevel(1)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=300) as server:
            # server.set_debuglevel(1)  # LOG_LEVEL == "DEBUG"일 때만 켜도 좋음
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)


def send_email(
    subject: str,
    body: str,
    to_addrs: List[str],
    attachments: List[Path],
    smtp: Dict[str, Any],
    sender_name: Optional[str] = None
):
    """
    Gmail이 중간에 연결 끊는 경우를 대비해서 최대 2회까지 재시도.
    """
    try:
        _send_email_once(subject, body, to_addrs, attachments, smtp, sender_name)
        return
    except SMTPServerDisconnected as e:
        log(f"SMTPServerDisconnected 발생(1차): {repr(e)} → 2초 후 재시도", "WARNING")
        time.sleep(2)
        # 한 번 더 시도
        _send_email_once(subject, body, to_addrs, attachments, smtp, sender_name)
    except Exception as e:
        log(f"SMTP 전송 중 기타 예외: {type(e).__name__} / {repr(e)}", "ERROR")
        raise

# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def run(target_rows: Optional[set[int]] = None) -> Dict[str, int]:
    """
    target_rows가 주어지면 그 로우(1-based)만 메일 전송.
    없으면 '작업 선택' == '이메일발송' 전체 대상.
    return: {"sent": n, "skipped": m}
    """
    creds = Credentials.from_service_account_file(
        CREDS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(SPREADSHEET_LINK)
    ws = sh.worksheet(TARGET_SHEET_NAME)

    # SMTP 설정은 .env에서 읽어온 전역값 사용
    smtp_cfg = {
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "user": SMTP_USER,
        "pass": SMTP_PASS,
    }
    log(f"SMTP CFG 체크: host={SMTP_HOST}, port={SMTP_PORT}, user={SMTP_USER}", "INFO")

    header = ws.row_values(HEADER_ROW)
    name_to_idx = {name: i + 1 for i, name in enumerate(header) if name}

    def need(col: str) -> int:
        if col not in name_to_idx:
            raise KeyError(f"시트에 '{col}' 열이 없습니다.")
        return name_to_idx[col]

    col_sel   = need("작업 선택")
    col_fname = need("다운로드파일명")
    # 옵션 열
    col_len   = name_to_idx.get("영상길이")
    col_link  = name_to_idx.get("쿠팡파트너스링크")
    col_scr   = name_to_idx.get("스크립트")
    col_insta = name_to_idx.get("인스타글내용")
    col_simpl = name_to_idx.get("간소화멘트")
    col_tt    = name_to_idx.get("틱톡멘트")
    col_to    = name_to_idx.get("수신이메일")
    col_done  = name_to_idx.get("작업 완료시간")  # (선택) 있으면 함께 기록 가능

    all_values = ws.get_all_values()
    total_rows = len(all_values)

    done_root = Path(__file__).resolve().parent / "done"

    sent = 0
    skipped = 0

    # 대상 행 결정
    if target_rows:
        candidates = sorted(set(r for r in target_rows if HEADER_ROW + 1 <= r <= total_rows))
    else:
        candidates = list(range(HEADER_ROW + 1, total_rows + 1))

    # 상태 변경(성공) 배치
    success_batch: List[Dict[str, Any]] = []
    BATCH_FLUSH_EVERY = 25

    for r in candidates:
        row = all_values[r - 1] if r - 1 < len(all_values) else []

        sel_val = (row[col_sel - 1] if len(row) >= col_sel else "").strip()

        # 반드시 '이메일발송'만
        if sel_val != "이메일발송":
            continue

        raw_name = (row[col_fname - 1] if len(row) >= col_fname else "").strip()
        if not raw_name:
            log(f"{r}행: 다운로드파일명 없음, 건너뜀", "WARNING")
            skipped += 1
            continue

        def getv(ci: Optional[int]) -> str:
            if not ci:
                return ""
            return (row[ci - 1] if len(row) >= ci else "").strip()

        rowdata = {
            "다운로드파일명": raw_name,
            "쿠팡파트너스링크": getv(col_link),
            "영상길이": getv(col_len),
            "스크립트": getv(col_scr),
            "인스타글내용": getv(col_insta),
            "간소화멘트": getv(col_simpl),
            "틱톡멘트": getv(col_tt),
        }

        fin_path, org_path = find_attachments(done_root, raw_name)
        attachments: List[Path] = []
        if fin_path and fin_path.exists():
            attachments.append(fin_path)
        if org_path and org_path.exists():
            attachments.append(org_path)

        # 영상길이 없으면 첨부에서 ffprobe로 계산
        if not rowdata["영상길이"]:
            base = fin_path or org_path
            sec = get_media_duration_seconds(base) if base else None
            if sec:
                rowdata["영상길이"] = sec_to_hms(sec)

        # 수신자: 시트 → EMAIL_TO(.env) → smtp_user
        row_to = (row[col_to - 1].strip() if col_to and len(row) >= col_to else "")
        if row_to:
            to_list = [x.strip() for x in row_to.split(",") if x.strip()]
        elif EMAIL_TO_DEFAULT:
            to_list = [x.strip() for x in EMAIL_TO_DEFAULT.split(",") if x.strip()]
        else:
            to_list = [smtp_user]

        subject = sanitize_name(rowdata["다운로드파일명"])
        body = build_body(rowdata)

        try:
            send_email(subject, body, to_list, attachments, smtp=smtp_cfg, sender_name=None)
            sent += 1
            log(f"{r}행: 메일 전송 완료 → {to_list}", "INFO")

            # 성공 시 상태 전환: 작업 선택 → 작업완료 (+ 선택: 완료시간)
            success_batch.append({
                "range": gspread.utils.rowcol_to_a1(r, col_sel),
                "values": [["작업완료"]],
            })
            if col_done:
                success_batch.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_done),
                    "values": [[datetime.now().strftime("%Y/%m/%d %H:%M")]],
                })
            if len(success_batch) >= BATCH_FLUSH_EVERY:
                safe_batch_update(ws, success_batch)
                success_batch.clear()

        except Exception as e:
            import traceback
            log(f"{r}행: 메일 전송 실패 → {type(e).__name__} / {repr(e)}", "ERROR")
            traceback.print_exc()
            skipped += 1

    # 남은 성공 상태 반영
    if success_batch:
        safe_batch_update(ws, success_batch)

    return {"sent": sent, "skipped": skipped}

def main():
    try:
        res = run(target_rows=None)
        log(f"완료: 전송 {res.get('sent',0)}건, 스킵 {res.get('skipped',0)}건", "INFO")
    except KeyboardInterrupt:
        log("중단됨", "WARNING")
        sys.exit(1)

if __name__ == "__main__":
    main()
