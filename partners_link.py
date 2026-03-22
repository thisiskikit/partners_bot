#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
partners_link.py  (Google Sheets 429 최소화 + '작업 선택' == '작업 시작' 필터)
- 시트(.env의 SPREADSHEET_LINK) '영상다운로드'(헤더 4행)에서
  '작업 선택' 값이 '작업 시작' 인 행만 대상으로,
  '키워드'를 쿠팡 검색 URL로 만들고 Coupang Affiliate Open API(deeplink)로 단축 파트너스 링크를 생성,
  '쿠팡파트너스링크' 열에 기록.
- 이미 값이 있으면 기본 스킵(덮어쓰지 않음). --force 옵션으로 덮어쓰기 가능(단, 대상은 '작업 시작' 행만).
- 스프레드시트 접근:
    · 읽기: 필요한 열만 batch_get 1회로 가져오기
    · 쓰기: batch_update로 묶어서 한 번에 반영 + 지수 백오프
"""

import os
import time
import hmac
import hashlib
import json
import random
import requests
from urllib.parse import quote
from typing import Dict, Any, List, Optional

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# 환경
# ──────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=".env")

SPREADSHEET_LINK = os.getenv("SPREADSHEET_LINK") or ""
CREDS_FILE       = os.getenv("CREDS_FILE_OHL1") or ""

ACCESS_KEY = os.getenv("COUPANG_ACCESS") or ""
SECRET_KEY = os.getenv("COUPANG_SECRET") or ""
SUB_ID     = os.getenv("COUPANG_SUB_ID", "")  # 없으면 빈 문자열 허용

DOMAIN     = os.getenv("COUPANG_DOMAIN", "https://api-gateway.coupang.com") or "https://api-gateway.coupang.com"
API_PREFIX = os.getenv("COUPANG_API_PREFIX", "/v2/providers/affiliate_open_api/apis/openapi/v1") or "/v2/providers/affiliate_open_api/apis/openapi/v1"

if not SPREADSHEET_LINK or not CREDS_FILE:
    raise RuntimeError("환경변수 SPREADSHEET_LINK / CREDS_FILE_OHL1 를 .env에 설정하세요.")
if not ACCESS_KEY or not SECRET_KEY:
    raise RuntimeError("환경변수 COUPANG_ACCESS / COUPANG_SECRET 를 .env에 설정하세요.")

SHEET_NAME = "영상다운로드"
HEADER_ROW = 4
TRIGGER_COL = "작업 선택"
TRIGGER_VALUE = "작업 시작"

# ──────────────────────────────────────────────────────────────
# Coupang Affiliate Deeplink
# ──────────────────────────────────────────────────────────────
def generate_hmac(method: str, path: str, query: str = "") -> str:
    """Coupang Open API HMAC-SHA256 Authorization 헤더 생성"""
    timestamp = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = timestamp + method + path + query
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, "
        f"signed-date={timestamp}, signature={signature}"
    )

def coupang_deeplink_for_search(keyword: str, sub_id: str = "") -> str:
    """
    키워드로 쿠팡 검색 URL을 만들고, /deeplink API로 파트너 링크를 생성한다.
    반환: 생성된 shortenUrl (없으면 landingUrl) — 실패 시 빈 문자열.
    """
    search_url = f"https://www.coupang.com/np/search?component=&q={quote(keyword)}&channel=user"

    path = f"{API_PREFIX}/deeplink"
    url  = f"{DOMAIN}{path}"
    body: Dict[str, Any] = {"coupangUrls": [search_url]}
    if sub_id:
        body["subId"] = sub_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": generate_hmac("POST", path, "")
    }

    # 간단 백오프 재시도
    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            arr  = data.get("data") or []
            if not arr:
                return ""
            entry = arr[0]
            return entry.get("shortenUrl") or entry.get("landingUrl") or ""
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(1.2 * attempt)  # 점진적 대기
                continue
            raise
        except requests.RequestException:
            if attempt < 3:
                time.sleep(1.2 * attempt)
                continue
            raise
    return ""

# ──────────────────────────────────────────────────────────────
# Google Sheets 유틸(429 최소화)
# ──────────────────────────────────────────────────────────────
def open_sheet():
    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gs = gspread.authorize(creds)
    sh = gs.open_by_url(SPREADSHEET_LINK)
    return sh.worksheet(SHEET_NAME)

def col_letter(col: int) -> str:
    s = ""
    while col:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s

def idx_map(ws) -> Dict[str, Optional[int]]:
    header = ws.row_values(HEADER_ROW)

    def req_idx(name: str) -> int:
        if name not in header:
            raise KeyError(f"시트에 '{name}' 열이 없습니다.")
        return header.index(name) + 1

    mapping = {
        # 필수 열
        TRIGGER_COL: req_idx(TRIGGER_COL),
        "키워드": req_idx("키워드"),
        "쿠팡파트너스링크": req_idx("쿠팡파트너스링크"),
        # 선택 열(있으면 사용)
        "작업 비고": (header.index("작업 비고") + 1) if "작업 비고" in header else None,
    }
    return mapping

def batch_get_needed(ws, idx: Dict[str, Optional[int]], start_row: int) -> Dict[str, List[str]]:
    """
    필요한 열만 open-ended range로 batch_get(호출 1회).
    반환 dict의 각 값은 1차원 리스트(행 순서 기준).
    """
    keys = [k for k in (TRIGGER_COL, "키워드", "쿠팡파트너스링크", "작업 비고") if idx.get(k)]
    ranges = [f"{col_letter(idx[k])}{start_row}:{col_letter(idx[k])}" for k in keys]
    values_list = ws.batch_get(ranges, value_render_option="UNFORMATTED_VALUE")
    max_len = max((len(v) for v in values_list), default=0)

    out: Dict[str, List[str]] = {}
    for k, col_vals in zip(keys, values_list):
        padded = col_vals + [[""]]*(max_len - len(col_vals))
        out[k] = [row[0] if row else "" for row in padded]

    # 존재하지 않았던 선택 키도 빈 리스트로 보정
    for k in ("작업 비고",):
        if k not in out:
            out[k] = []
    return out

def batch_update_with_backoff(ws, requests: List[Dict], max_attempts: int = 5) -> None:
    """429/일시 오류 대비 지수 백오프 batch_update"""
    if not requests:
        return
    attempt = 1
    while True:
        try:
            ws.batch_update(requests)
            return
        except HttpError as e:
            msg = str(e).lower()
            is_rate = ("too many requests" in msg) or ("rate limit" in msg)
            status = getattr(getattr(e, "resp", None), "status", None)
            if (status == 429 or is_rate) and attempt < max_attempts:
                sleep_s = (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)  # 지터
                time.sleep(sleep_s)
                attempt += 1
                continue
            raise

# ──────────────────────────────────────────────────────────────
# 메인 로직
# ──────────────────────────────────────────────────────────────
def _should_start(cell_value: str) -> bool:
    """
    '작업 선택' 열의 값이 '작업 시작'(대/소문자/공백 무시)일 때만 True
    """
    return cell_value.strip().lower() == TRIGGER_VALUE.lower()

def process(force: bool = False):
    """
    force=False: '작업 선택' == '작업 시작' 표시된 행 중 '쿠팡파트너스링크'가 비어 있는 행만 생성
    force=True : 동일 대상(작업 시작 행)에서 기존 값이 있어도 덮어쓰기
    """
    ws = open_sheet()
    idx = idx_map(ws)

    data_start = HEADER_ROW + 1

    # 읽기 1회: 필요한 열만
    cols = batch_get_needed(ws, idx, data_start)
    start_flags = cols[TRIGGER_COL]          # ← '작업 선택'
    keywords    = cols["키워드"]
    exist_links = cols["쿠팡파트너스링크"]

    n = max(len(start_flags), len(keywords), len(exist_links))
    to_write: List[Dict] = []
    error_writes: List[Dict] = []

    # 쿠팡 API 호출 간 소폭 딜레이(외부 API 429 예방)
    def small_pause(step: float = 0.3):
        time.sleep(random.uniform(step * 0.6, step * 1.4))

    for i in range(n):
        rownum  = data_start + i
        start_v = (start_flags[i] if i < len(start_flags) else "")
        if not _should_start(start_v):
            # '작업 선택' 값이 '작업 시작'이 아니면 스킵
            continue

        keyword = (keywords[i] if i < len(keywords) else "").strip()
        current = (exist_links[i] if i < len(exist_links) else "").strip()

        if not keyword:
            continue
        if current and not force:
            continue

        try:
            stage = "DEEPLINK_CALL"
            link = coupang_deeplink_for_search(keyword, SUB_ID)
            if not link:
                raise RuntimeError("딥링크 API 결과가 비었습니다.")

            to_write.append({
                "range": gspread.utils.rowcol_to_a1(rownum, idx["쿠팡파트너스링크"]),
                "values": [[link]]
            })

            # 묶음이 너무 커지면 중간 커밋
            if len(to_write) >= 300:
                batch_update_with_backoff(ws, to_write)
                to_write.clear()

            small_pause(0.25)

        except Exception as e:
            note = f"[단계] {stage if 'stage' in locals() else 'INIT'}\n[에러] {type(e).__name__}: {e}\n[키워드] {keyword}"
            if idx.get("작업 비고"):
                error_writes.append({
                    "range": gspread.utils.rowcol_to_a1(rownum, idx["작업 비고"]),
                    "values": [[note[:1800]]]
                })

            if error_writes:
                batch_update_with_backoff(ws, error_writes)
                error_writes.clear()
            continue

    # 남은 성공/에러 쓰기 반영
    if to_write:
        batch_update_with_backoff(ws, to_write)
    if error_writes:
        batch_update_with_backoff(ws, error_writes)

    print("✅ 쿠팡 파트너스 링크 생성 작업 완료")

# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="쿠팡 파트너스 링크 생성기")
    ap.add_argument("--force", action="store_true", help="기존 값을 덮어쓰고 재생성 (단, '작업 선택'이 '작업 시작'인 행만)")
    args = ap.parse_args()
    process(force=args.force)
