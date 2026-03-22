#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, time, traceback, subprocess, json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
import re

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
import gspread.utils as A1

# ─────────────────────────────────────────
# 환경변수 검증/해결
# ─────────────────────────────────────────
def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not str(v).strip():
        raise RuntimeError(f"환경변수 {name} 가 비어있습니다. .env에 설정하세요.")
    return str(v).strip()

SHEET_URL = must_env("SPREADSHEET_LINK")
CREDS     = must_env("CREDS_FILE_OHL2")  # 서비스 계정 JSON 경로 또는 JSON 문자열

def resolve_creds(creds_value: str) -> str:
    """서비스계정 값이 경로면 그대로, JSON 문자열이면 임시파일로 저장 후 그 경로 반환"""
    p = Path(creds_value)
    if p.exists():
        return str(p.resolve())
    try:
        data = json.loads(creds_value)
        tmp = Path.cwd() / ".sa_tmp.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(tmp.resolve())
    except Exception:
        # 🔧 메시지 내 변수명 타이포 수정(OHL1 → OHL2)
        raise RuntimeError(
            "CREDS_FILE_OHL2 값이 유효한 파일 경로도, 올바른 JSON 문자열도 아닙니다. "
            "서비스 계정 파일 경로를 넣거나 JSON 내용을 그대로 넣어 주세요."
        )

CREDS_RESOLVED = resolve_creds(CREDS)

QUEUE_SHEET = "queue"
WORKER_ID   = os.getenv("WORKER_ID", os.getlogin())
POLL_SEC    = float(os.getenv("POLL_SEC", "2.0"))

# 내부 플래그: stop_soft 요청 시 루프 종료용
_STOP_SOFT_REQUESTED = False

# ─────────────────────────────────────────
# 공용 유틸
# ─────────────────────────────────────────
def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def gc_open():
    creds = Credentials.from_service_account_file(
        CREDS_RESOLVED,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds).open_by_url(SHEET_URL)

# ── Sheets 안전 읽기(429 백오프 + 스로틀)
_read_last_ts = 0.0  # 프로세스 전역 최소 간격 스로틀용

def _throttle_reads(min_interval=0.35):
    """연속 read 사이 최소 간격 확보(분당 요청 수 완화)."""
    global _read_last_ts
    now_t = time.monotonic()
    dt = now_t - _read_last_ts
    if dt < min_interval:
        time.sleep(min_interval - dt)
    _read_last_ts = time.monotonic()

def _is_transient_api_error(e: Exception) -> bool:
    msg = str(e)
    return any(code in msg for code in ("429", "500", "502", "503", "504"))

def safe_batch_get(ws, ranges: List[str], *, max_attempts=7, base=1.7, max_sleep=60.0):
    """ws.batch_get(ranges)를 429/5xx에서 지수 백오프(+지터)로 재시도."""
    import random
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.batch_get(ranges)
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            print(f"[worker] Sheets 읽기 대기… 재시도 {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

def safe_row_values(ws, row: int) -> List[str]:
    """row 전체를 안전하게 읽어 1차원 리스트로 반환."""
    rng = f"{row}:{row}"
    res = safe_batch_get(ws, [rng])
    if not res or not res[0]:
        return []
    return res[0][0]

def safe_ws_batch_update(ws, requests: List[Dict[str, Any]], *, max_attempts=7, base=1.6, max_sleep=60.0):
    """ws.batch_update를 429/5xx에서 지수 백오프로 재시도."""
    import random
    if not requests:
        return
    for attempt in range(1, max_attempts + 1):
        try:
            ws.batch_update(requests)
            return
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            print(f"[worker] Sheets 쓰기 대기… 재시도 {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

# ─────────────────────────────────────────
# queue 시트 접근
# ─────────────────────────────────────────
def idx_map(ws) -> Dict[str, int]:
    head = safe_row_values(ws, 1)  # 안전화
    return {h: i + 1 for i, h in enumerate(head) if h}

def _col_letter(col_idx: int) -> str:
    # 1 -> A, 2 -> B ...
    a1 = A1.rowcol_to_a1(1, col_idx)   # 예: "C1"
    return re.sub(r"\d+", "", a1)      # -> "C"

def claim_one(ws) -> Optional[Dict[str, Any]]:
    idx = idx_map(ws)
    need_cols = ["status", "claimed_by", "started_at"]
    if not all(c in idx for c in need_cols):
        raise RuntimeError("queue 시트에 status/claimed_by/started_at 헤더가 필요합니다.")

    start_row = 2

    st_col = _col_letter(idx["status"])
    cl_col = _col_letter(idx["claimed_by"])

    # ✅ end_row를 쓰지 않고 열 끝까지 읽기
    status_rng  = f"{st_col}{start_row}:{st_col}"
    claimed_rng = f"{cl_col}{start_row}:{cl_col}"

    res = safe_batch_get(ws, [status_rng, claimed_rng]) or [[], []]
    status_col  = [r[0] if r else "" for r in (res[0] or [])]
    claimed_col = [r[0] if r else "" for r in (res[1] or [])]
    n = max(len(status_col), len(claimed_col))

    target_row_index = None
    for i in range(n):
        st = (status_col[i] if i < len(status_col) else "").strip()
        cl = (claimed_col[i] if i < len(claimed_col) else "").strip()
        if st == "pending" and not cl:
            target_row_index = start_row + i
            break

    if target_row_index is None:
        return None

    updates = [
        {"range": A1.rowcol_to_a1(target_row_index, idx["status"]),     "values": [["running"]]},
        {"range": A1.rowcol_to_a1(target_row_index, idx["claimed_by"]), "values": [[WORKER_ID]]},
        {"range": A1.rowcol_to_a1(target_row_index, idx["started_at"]), "values": [[now()]]},
    ]
    safe_ws_batch_update(ws, updates)

    row_vals = safe_row_values(ws, target_row_index)
    data = {}
    for name, col in idx.items():
        data[name] = row_vals[col - 1] if len(row_vals) >= col else ""
    data["_row"] = target_row_index
    return data

def finish(ws, r: int, *, ok=True, err: str = ""):
    idx = idx_map(ws)
    updates = [
        {"range": A1.rowcol_to_a1(r, idx["finished_at"]), "values": [[now()]]},
        {"range": A1.rowcol_to_a1(r, idx["status"]),      "values": [["done" if ok else "error"]]},
    ]
    if not ok and "error" in idx:
        updates.append({"range": A1.rowcol_to_a1(r, idx["error"]), "values": [[err[:1800]]]}
        )
    safe_ws_batch_update(ws, updates)

# ─────────────────────────────────────────
# 작업 실행기 (main.py 함수 호출 + stop 명령 처리)
# ─────────────────────────────────────────
class StopSoft(Exception):
    """부드러운 정지 요청: 현재 작업 마치고 루프 종료"""
    pass

class StopNow(Exception):
    """즉시 종료 요청"""
    pass

def call_main_func(cmd: str):
    """
    main.py 내 함수 직접 호출 (서브프로세스, 1회 실행)
    - link_download -> run_link_video_download_only
    - tts_email     -> run_tts_and_email_only
    - pipeline      -> run_video_pipeline
    - inpock        -> run_inpock_upload
    - send_email    -> send_email.run(None)
    - stop_soft     -> soft stop(루프 종료 신호)
    - stop_now      -> 즉시 종료
    """
    if cmd == "stop_soft":
        # 루프 밖에서 처리하기 위해 신호만 던짐
        raise StopSoft("soft stop requested")
    if cmd == "stop_now":
        raise StopNow("immediate stop requested")

    py = sys.executable
    if cmd == "link_download":
        code = "import logging,main; logging.basicConfig(level=logging.INFO); main.run_link_video_download_only(logging.getLogger('worker'), None)"
    elif cmd == "tts_email":
        code = "import logging,main; logging.basicConfig(level=logging.INFO); main.run_tts_and_email_only(logging.getLogger('worker'), None)"
    elif cmd == "pipeline":
        code = "import logging,main; logging.basicConfig(level=logging.INFO); main.run_video_pipeline(logging.getLogger('worker'), None)"
    elif cmd == "inpock":
        code = "import logging,main; logging.basicConfig(level=logging.INFO); main.run_inpock_upload(logging.getLogger('worker'), None)"
    elif cmd == "send_email":
        code = "import send_email as se; print(se.run(None))"
    else:
        raise ValueError(f"unknown cmd: {cmd}")

    subprocess.run([py, "-c", code], check=True)

# ─────────────────────────────────────────
# 메인 루프
# ─────────────────────────────────────────
def loop():
    global _STOP_SOFT_REQUESTED
    ss = gc_open()
    wsq = ss.worksheet(QUEUE_SHEET)
    print(f"[worker] started as {WORKER_ID}, polling {POLL_SEC}s")

    while True:
        try:
            # stop_soft가 요청된 상태면 더 이상 새로운 작업을 잡지 않고 종료
            if _STOP_SOFT_REQUESTED:
                print("[worker] soft stop requested earlier; exiting loop gracefully.")
                break

            task = claim_one(wsq)
            if not task:
                time.sleep(POLL_SEC)
                continue

            try:
                cmd = str(task.get("cmd", "")).strip()
                if not cmd:
                    raise ValueError("queue.cmd 가 비어있습니다.")
                print(f"[worker] claim: row={task['_row']} cmd={cmd} by={WORKER_ID}")

                # 실행
                try:
                    call_main_func(cmd)
                    finish(wsq, task["_row"], ok=True)
                    print(f"[worker] done : row={task['_row']} cmd={cmd}")
                except StopSoft as se:
                    # 명령 행은 정상 완료로 마킹하고, 플래그 세운 뒤 루프 종료
                    finish(wsq, task["_row"], ok=True)
                    print(f"[worker] soft stop acknowledged: {se}. Exiting after marking done.")
                    _STOP_SOFT_REQUESTED = True
                    # 다음 루프에서 break 되도록 함
                except StopNow as sn:
                    # 명령 행을 완료 처리 후 즉시 종료
                    finish(wsq, task["_row"], ok=True)
                    print(f"[worker] immediate stop acknowledged: {sn}. Exiting now.")
                    return  # 즉시 프로세스 종료

            except Exception as e:
                err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                print(f"[worker] error while running task row={task.get('_row')} : {e}")
                try:
                    finish(wsq, task["_row"], ok=False, err=err)
                except Exception as e2:
                    print(f"[worker] finish() failed: {e2}")

        except APIError as e:
            print(f"[worker] APIError: {e} — sleeping…")
            time.sleep(POLL_SEC * 2)
        except Exception as e:
            print(f"[worker] loop error: {e} — sleeping…")
            time.sleep(POLL_SEC * 2)

if __name__ == "__main__":
    loop()

