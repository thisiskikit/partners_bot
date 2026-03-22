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

# ✅ 스프레드시트 링크 (env 이름은 그대로 두되, 필요하면 바꾸셔도 됩니다)
SHEET_URL = must_env("SPREADSHEET_LINK_inpock")
CREDS     = must_env("CREDS_FILE_INPOCK")  # 서비스 계정 JSON 경로 또는 JSON 문자열

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
        raise RuntimeError(
            "CREDS_FILE_INPOCK 값이 유효한 파일 경로도, 올바른 JSON 문자열도 아닙니다. "
            "서비스 계정 파일 경로를 넣거나 JSON 내용을 그대로 넣어 주세요."
        )

CREDS_RESOLVED = resolve_creds(CREDS)

QUEUE_SHEET = os.getenv("QUEUE_SHEET", "queue").strip()
WORKER_ID   = os.getenv("WORKER_ID", os.getlogin()).strip()
POLL_SEC    = float(os.getenv("POLL_SEC", "2.0"))

# ✅ insta_download.py 경로(기본: 이 worker 파일과 같은 폴더)
INSTA_DOWNLOAD_PY = os.getenv("INSTA_DOWNLOAD_PY", "insta_download.py").strip()

# 내부 플래그
_STOP_SOFT = False

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
_read_last_ts = 0.0

def _throttle_reads(min_interval=0.35):
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
    import random
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.batch_get(ranges)
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            print(f"[insta-worker] Sheets 읽기 대기… 재시도 {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

def safe_row_values(ws, row: int) -> List[str]:
    rng = f"{row}:{row}"
    res = safe_batch_get(ws, [rng])
    if not res or not res[0]:
        return []
    return res[0][0]

def safe_ws_batch_update(ws, requests: List[Dict[str, Any]], *, max_attempts=7, base=1.6, max_sleep=60.0):
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
            print(f"[insta-worker] Sheets 쓰기 대기… 재시도 {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

# ─────────────────────────────────────────
# queue 시트 접근
# ─────────────────────────────────────────
def idx_map(ws) -> Dict[str, int]:
    head = safe_row_values(ws, 1)
    return {h: i + 1 for i, h in enumerate(head) if h}

def _col_letter(col_idx: int) -> str:
    a1 = A1.rowcol_to_a1(1, col_idx)   # 예: "C1"
    return re.sub(r"\d+", "", a1)      # -> "C"

def claim_one(ws) -> Optional[Dict[str, Any]]:
    idx = idx_map(ws)
    need_cols = ["status", "claimed_by", "started_at", "finished_at", "cmd"]
    missing = [c for c in need_cols if c not in idx]
    if missing:
        raise RuntimeError(f"queue 시트 헤더가 부족합니다. 누락: {missing}")

    start_row = 2
    st_col = _col_letter(idx["status"])
    cl_col = _col_letter(idx["claimed_by"])

    # (주의) 오픈엔드 범위는 빈행 압축 이슈가 있을 수 있습니다.
    # 기존 방식을 유지하되, 문제가 지속되면 "고정 블록 스캔" 방식으로 바꾸는 것을 권장합니다.
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
    if (not ok) and ("error" in idx):
        updates.append({"range": A1.rowcol_to_a1(r, idx["error"]), "values": [[err[:1800]]]} )
    safe_ws_batch_update(ws, updates)

# ─────────────────────────────────────────
# 작업 실행기 (insta_download 전용)
# ─────────────────────────────────────────
class StopSoft(Exception): pass
class StopNow(Exception): pass

def call_job(cmd: str):
    """
    ✅ insta_download 전용 worker:
    - insta_download -> insta_download.py 실행
    - stop_soft/stop_now 지원
    """
    cmd = (cmd or "").strip()

    if cmd == "stop_soft":
        raise StopSoft("soft stop requested")
    if cmd == "stop_now":
        raise StopNow("immediate stop requested")

    if cmd != "insta_download":
        raise ValueError(f"insta-worker는 'insta_download' 작업만 처리합니다. (got: {cmd})")

    # ✅ insta_download.py 실행
    py = sys.executable
    script_path = Path(INSTA_DOWNLOAD_PY)
    if not script_path.exists():
        # worker 기준 상대경로 허용
        script_path = (Path(__file__).resolve().parent / INSTA_DOWNLOAD_PY).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"insta_download.py 를 찾지 못했습니다: {INSTA_DOWNLOAD_PY}")

    subprocess.run([py, str(script_path)], check=True)

# ─────────────────────────────────────────
# 메인 루프
# ─────────────────────────────────────────
def loop():
    global _STOP_SOFT
    ss = gc_open()
    wsq = ss.worksheet(QUEUE_SHEET)
    print(f"[insta-worker] started as {WORKER_ID} / sheet={SHEET_URL} / queue={QUEUE_SHEET} / polling={POLL_SEC}s")
    print(f"[insta-worker] script={INSTA_DOWNLOAD_PY}")

    while True:
        try:
            if _STOP_SOFT:
                print("[insta-worker] soft stop requested earlier; exiting loop gracefully.")
                break

            task = claim_one(wsq)
            if not task:
                time.sleep(POLL_SEC)
                continue

            try:
                cmd = str(task.get("cmd", "")).strip()
                if not cmd:
                    raise ValueError("queue.cmd 가 비어있습니다.")

                print(f"[insta-worker] claim: row={task['_row']} cmd={cmd} by={WORKER_ID}")

                try:
                    call_job(cmd)
                    finish(wsq, task["_row"], ok=True)
                    print(f"[insta-worker] done : row={task['_row']} cmd={cmd}")

                except StopSoft as se:
                    finish(wsq, task["_row"], ok=True)
                    print(f"[insta-worker] soft stop acknowledged: {se}. Exiting after marking done.")
                    _STOP_SOFT = True

                except StopNow as sn:
                    finish(wsq, task["_row"], ok=True)
                    print(f"[insta-worker] immediate stop acknowledged: {sn}. Exiting now.")
                    return

            except Exception as e:
                err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                print(f"[insta-worker] error while running task row={task.get('_row')} : {e}")
                try:
                    finish(wsq, task["_row"], ok=False, err=err)
                except Exception as e2:
                    print(f"[insta-worker] finish() failed: {e2}")

        except APIError as e:
            print(f"[insta-worker] APIError: {e} — sleeping…")
            time.sleep(POLL_SEC * 2)
        except Exception as e:
            print(f"[insta-worker] loop error: {e} — sleeping…")
            time.sleep(POLL_SEC * 2)

if __name__ == "__main__":
    loop()
