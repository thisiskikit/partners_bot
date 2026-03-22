#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
worker_voice_gen.py (Google Sheets polling queue 버전 / WebApp 미사용) - 요청량/겹침 최소화 강화 버전

전제:
- 스프레드시트에 queue 시트가 존재: 기본 'queue_voice_gen'
- queue 시트 헤더(1행)는 아래 컬럼들을 포함해야 함 (이름 정확히):
  created_at, updated_at, job_id, job_type, status, attempts, max_attempts,
  lease_until, worker_id, source_sheet, source_row, payload_json, result_json, last_error

동작:
1) queue 시트에서 PENDING + (lease 없음 or 만료) + attempts < max_attempts 인 row를 찾음
2) RUNNING으로 클레임(status/worker_id/lease_until/attempts/updated_at 갱신) 후 리드백 검증
3) payload_json 또는 source_row 기반으로 TARGET_ROW를 만들어 voice_gen.py를 단건 실행
4) 성공: DONE + result_json 기록
   실패: ERROR + last_error 기록

요청량(겹침) 최소화 강화:
- POLL_SEC 기본값을 10초로 상향(기존 2초보다 훨씬 덜 읽음)
- 큐가 비어있으면 idle backoff로 점점 더 느리게(최대 IDLE_MAX_SEC)
- READ_THROTTLE_SEC / WRITE_THROTTLE_SEC 로 읽기/쓰기 최소 간격 강제
- Sheets 429/5xx 에서 지수 백오프 재시도

필수 ENV(.env 권장):
- SPREADSHEET_LINK_voice (또는 SPREADSHEET_LINK)
- CREDS_FILE_OHL1 (또는 CREDS_FILE_OHL2 / GOOGLE_APPLICATION_CREDENTIALS)
- VOICE_GEN_SCRIPT (voice_gen.py 경로)

선택 ENV(권장):
- PYTHON_BIN (venv python 경로)
- QUEUE_SHEET (기본 queue_voice_gen)
- WORKER_ID (기본 hostname 기반)
- POLL_SEC (기본 10.0)
- CLAIM_LEASE_MINUTES (기본 30)
- MAX_STD_TAIL_CHARS (기본 4000)

요청량 더 줄이는 옵션(권장):
- READ_THROTTLE_SEC (기본 1.2)
- WRITE_THROTTLE_SEC (기본 1.0)
- IDLE_MAX_SEC (기본 60)
- IDLE_BACKOFF_MULT (기본 1.4)
- IDLE_JITTER_SEC (기본 0.7)
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import traceback
import subprocess
import re
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
import gspread.utils as A1


# ─────────────────────────────────────────
# .env 로드(이 파일 위치 기준)
# ─────────────────────────────────────────
DOTENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)


# ─────────────────────────────────────────
# ENV 유틸
# ─────────────────────────────────────────
def _clean(s: Optional[str]) -> str:
    return (s or "").strip().strip('"').strip("'").replace("\u200b", "").replace("\ufeff", "")

def must_env(name: str) -> str:
    v = _clean(os.getenv(name))
    if not v:
        raise RuntimeError(f"환경변수 {name} 가 비어있습니다. .env에 설정하세요.")
    return v

def env_first(*names: str) -> str:
    for n in names:
        v = _clean(os.getenv(n))
        if v:
            return v
    return ""


# ─────────────────────────────────────────
# ENV 설정
# ─────────────────────────────────────────
# 요청하신 대로 변수명을 voice 전용으로 쓰시되, 혹시 기존 변수도 잡히면 자동 fallback
SPREADSHEET_LINK = env_first("SPREADSHEET_LINK_voice", "SPREADSHEET_LINK")
if not SPREADSHEET_LINK:
    raise RuntimeError("환경변수 SPREADSHEET_LINK_voice(또는 SPREADSHEET_LINK) 가 비어있습니다. .env에 설정하세요.")

CREDS_RAW = env_first("CREDS_FILE_OHL1", "CREDS_FILE_OHL2", "GOOGLE_APPLICATION_CREDENTIALS")
if not CREDS_RAW:
    raise RuntimeError("CREDS_FILE_OHL1(또는 CREDS_FILE_OHL2 / GOOGLE_APPLICATION_CREDENTIALS) 를 .env에 설정하세요.")

VOICE_GEN_SCRIPT = must_env("VOICE_GEN_SCRIPT")
PYTHON_BIN = _clean(os.getenv("PYTHON_BIN"))

QUEUE_SHEET = _clean(os.getenv("QUEUE_SHEET")) or "queue_voice_gen"

# ✅ 요청량 줄이기: 기본 폴링을 10초로 상향
POLL_SEC = float(_clean(os.getenv("POLL_SEC")) or "10.0")

CLAIM_LEASE_MINUTES = int(_clean(os.getenv("CLAIM_LEASE_MINUTES")) or "30")
MAX_STD_TAIL_CHARS = int(_clean(os.getenv("MAX_STD_TAIL_CHARS")) or "4000")

WORKER_ID = _clean(os.getenv("WORKER_ID")) or f"voicegen-{socket.gethostname()}"

# ✅ 읽기/쓰기 최소 간격(겹침 억제)
READ_THROTTLE_SEC  = float(_clean(os.getenv("READ_THROTTLE_SEC")) or "1.2")
WRITE_THROTTLE_SEC = float(_clean(os.getenv("WRITE_THROTTLE_SEC")) or "1.0")

# ✅ idle backoff (큐가 비면 점점 느리게)
IDLE_MAX_SEC      = float(_clean(os.getenv("IDLE_MAX_SEC")) or "60")
IDLE_BACKOFF_MULT = float(_clean(os.getenv("IDLE_BACKOFF_MULT")) or "1.4")
IDLE_JITTER_SEC   = float(_clean(os.getenv("IDLE_JITTER_SEC")) or "0.7")

VOICE_GEN_SCRIPT_PATH = Path(VOICE_GEN_SCRIPT).expanduser().resolve()
if not VOICE_GEN_SCRIPT_PATH.is_file():
    raise FileNotFoundError(f"VOICE_GEN_SCRIPT 파일을 찾을 수 없습니다: {VOICE_GEN_SCRIPT_PATH}")

PYTHON_BIN_PATH: Optional[Path] = None
if PYTHON_BIN:
    PYTHON_BIN_PATH = Path(PYTHON_BIN).expanduser().resolve()
    if not PYTHON_BIN_PATH.is_file():
        raise FileNotFoundError(f"PYTHON_BIN 파일을 찾을 수 없습니다: {PYTHON_BIN_PATH}")


# ─────────────────────────────────────────
# creds 해결(경로 or JSON문자열)
# ─────────────────────────────────────────
def resolve_creds(creds_value: str) -> str:
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
            "CREDS 값이 유효한 파일 경로도, 올바른 JSON 문자열도 아닙니다. "
            "서비스 계정 파일 경로를 넣거나 JSON 내용을 그대로 넣어 주세요."
        )

CREDS_RESOLVED = resolve_creds(CREDS_RAW)


# ─────────────────────────────────────────
# Sheets 안전 read/write(429 백오프) + 스로틀
# ─────────────────────────────────────────
_read_last_ts = 0.0
_write_last_ts = 0.0

def _throttle_reads(min_interval: Optional[float] = None):
    global _read_last_ts
    if min_interval is None:
        min_interval = READ_THROTTLE_SEC
    now_t = time.monotonic()
    dt = now_t - _read_last_ts
    if dt < min_interval:
        time.sleep(min_interval - dt)
    _read_last_ts = time.monotonic()

def _throttle_writes(min_interval: Optional[float] = None):
    global _write_last_ts
    if min_interval is None:
        min_interval = WRITE_THROTTLE_SEC
    now_t = time.monotonic()
    dt = now_t - _write_last_ts
    if dt < min_interval:
        time.sleep(min_interval - dt)
    _write_last_ts = time.monotonic()

def _is_transient_api_error(e: Exception) -> bool:
    msg = str(e)
    return any(code in msg for code in ("429", "500", "502", "503", "504"))

def safe_batch_get(ws, ranges: List[str], *, max_attempts=7, base=1.7, max_sleep=60.0):
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.batch_get(ranges)
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            print(f"[worker_voice_gen] Sheets read backoff {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

def safe_row_values(ws, row: int) -> List[str]:
    res = safe_batch_get(ws, [f"{row}:{row}"])
    if not res or not res[0]:
        return []
    return res[0][0]

def safe_ws_batch_update(ws, requests: List[Dict[str, Any]], *, max_attempts=7, base=1.6, max_sleep=60.0):
    if not requests:
        return
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_writes()
            ws.batch_update(requests)
            return
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            print(f"[worker_voice_gen] Sheets write backoff {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            time.sleep(sleep_s)

def now_iso() -> str:
    # UTC aware ISO로 통일 (lease 비교/만료 판단 안정화)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _col_letter(col_idx: int) -> str:
    a1 = A1.rowcol_to_a1(1, col_idx)   # e.g. "C1"
    return re.sub(r"\d+", "", a1)      # -> "C"

def parse_iso_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ─────────────────────────────────────────
# Sheets 연결
# ─────────────────────────────────────────
def gc_open():
    creds = Credentials.from_service_account_file(
        CREDS_RESOLVED,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds).open_by_url(SPREADSHEET_LINK)

def idx_map(ws) -> Dict[str, int]:
    head = safe_row_values(ws, 1)
    return {h: i + 1 for i, h in enumerate(head) if h}


# ─────────────────────────────────────────
# Queue claim/finish
# ─────────────────────────────────────────
REQUIRED_HEADERS = [
    "created_at","updated_at","job_id","job_type","status","attempts","max_attempts",
    "lease_until","worker_id","source_sheet","source_row","payload_json","result_json","last_error"
]

def assert_queue_headers(ws):
    idx = idx_map(ws)
    missing = [h for h in REQUIRED_HEADERS if h not in idx]
    if missing:
        raise RuntimeError(f"{QUEUE_SHEET} 시트 헤더가 부족합니다: {missing}")
    return idx

def claim_one(wsq) -> Optional[Dict[str, Any]]:
    """
    PENDING + (lease 없음 or 만료) + attempts < max_attempts 를 1건 클레임
    레이스 완화를 위해:
      - 먼저 RUNNING으로 찍고
      - 해당 row를 재읽어서 worker_id가 나인지 확인(리드백 검증)
    """
    idx = assert_queue_headers(wsq)
    start_row = 2

    c_status = _col_letter(idx["status"])
    c_lease  = _col_letter(idx["lease_until"])
    c_att    = _col_letter(idx["attempts"])
    c_max    = _col_letter(idx["max_attempts"])

    # 끝행을 특정하지 않고 끝까지 읽기
    rng_status = f"{c_status}{start_row}:{c_status}"
    rng_lease  = f"{c_lease}{start_row}:{c_lease}"
    rng_att    = f"{c_att}{start_row}:{c_att}"
    rng_max    = f"{c_max}{start_row}:{c_max}"

    res = safe_batch_get(wsq, [rng_status, rng_lease, rng_att, rng_max]) or [[], [], [], []]
    col_status = [r[0] if r else "" for r in (res[0] or [])]
    col_lease  = [r[0] if r else "" for r in (res[1] or [])]
    col_att    = [r[0] if r else "" for r in (res[2] or [])]
    col_max    = [r[0] if r else "" for r in (res[3] or [])]

    n = max(len(col_status), len(col_lease), len(col_att), len(col_max))
    if n <= 0:
        return None

    now_dt = datetime.now(timezone.utc)

    def lease_expired(v: str) -> bool:
        dt = parse_iso_dt(v)
        if not dt:
            return True
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= now_dt

    for i in range(n):
        row_no = start_row + i
        st = (col_status[i] if i < len(col_status) else "").strip()
        lease = (col_lease[i] if i < len(col_lease) else "").strip()
        att = (col_att[i] if i < len(col_att) else "0")
        mx  = (col_max[i] if i < len(col_max) else "3")

        if st != "PENDING":
            continue

        try:
            att_i = int(str(att).strip() or "0")
            mx_i  = int(str(mx).strip() or "3")
        except Exception:
            continue

        if att_i >= mx_i:
            continue

        if lease and not lease_expired(lease):
            continue

        # claim 시도
        lease_until = (now_dt + timedelta(minutes=CLAIM_LEASE_MINUTES)).replace(microsecond=0).isoformat()

        updates = [
            {"range": A1.rowcol_to_a1(row_no, idx["status"]),      "values": [["RUNNING"]]},
            {"range": A1.rowcol_to_a1(row_no, idx["worker_id"]),   "values": [[WORKER_ID]]},
            {"range": A1.rowcol_to_a1(row_no, idx["lease_until"]), "values": [[lease_until]]},
            {"range": A1.rowcol_to_a1(row_no, idx["attempts"]),    "values": [[att_i + 1]]},
            {"range": A1.rowcol_to_a1(row_no, idx["updated_at"]),  "values": [[now_iso()]]},
        ]
        safe_ws_batch_update(wsq, updates)

        # 리드백 검증(내가 클레임했는지)
        row_vals = safe_row_values(wsq, row_no)
        cur_worker = (row_vals[idx["worker_id"] - 1] if len(row_vals) >= idx["worker_id"] else "").strip()
        cur_status = (row_vals[idx["status"] - 1] if len(row_vals) >= idx["status"] else "").strip()
        if cur_worker != WORKER_ID or cur_status != "RUNNING":
            continue

        data: Dict[str, Any] = {}
        for name, col in idx.items():
            data[name] = row_vals[col - 1] if len(row_vals) >= col else ""
        data["_row"] = row_no
        return data

    return None

def finish(wsq, row_no: int, *, ok: bool, result_json: str = "", err: str = ""):
    idx = assert_queue_headers(wsq)
    updates = [
        {"range": A1.rowcol_to_a1(row_no, idx["status"]),      "values": [["DONE" if ok else "ERROR"]]},
        {"range": A1.rowcol_to_a1(row_no, idx["lease_until"]), "values": [[""]]},
        {"range": A1.rowcol_to_a1(row_no, idx["updated_at"]),  "values": [[now_iso()]]},
    ]
    if result_json:
        updates.append({"range": A1.rowcol_to_a1(row_no, idx["result_json"]), "values": [[result_json[:1800]]]})
    if err:
        updates.append({"range": A1.rowcol_to_a1(row_no, idx["last_error"]),  "values": [[err[:1800]]]})
    safe_ws_batch_update(wsq, updates)


# ─────────────────────────────────────────
# voice_gen 실행
# ─────────────────────────────────────────
def _tail(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[-n:]

def run_voice_gen_for_target(target_row: int, payload: Dict[str, Any]) -> Tuple[int, str, str, float]:
    child_env = os.environ.copy()
    child_env["TARGET_ROW"] = str(target_row)

    # (선택) payload 기반 주입: voice_gen.py에서 읽을 수 있음
    if payload.get("sheet_name"):
        child_env["SHEET_NAME"] = str(payload["sheet_name"])
    if payload.get("header_row"):
        child_env["HEADER_ROW"] = str(payload["header_row"])

    py = str(PYTHON_BIN_PATH) if PYTHON_BIN_PATH else sys.executable
    cmd = [py, str(VOICE_GEN_SCRIPT_PATH)]

    start = time.time()
    p = subprocess.run(
        cmd,
        env=child_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    elapsed = time.time() - start
    return p.returncode, p.stdout or "", p.stderr or "", elapsed


# ─────────────────────────────────────────
# 메인 루프 (idle backoff 적용)
# ─────────────────────────────────────────
def loop():
    ss = gc_open()
    wsq = ss.worksheet(QUEUE_SHEET)

    print(f"[worker_voice_gen] started as {WORKER_ID}")
    print(f"[worker_voice_gen] spreadsheet={SPREADSHEET_LINK}")
    print(f"[worker_voice_gen] queue={QUEUE_SHEET}, POLL_SEC={POLL_SEC}")
    print(f"[worker_voice_gen] READ_THROTTLE_SEC={READ_THROTTLE_SEC}, WRITE_THROTTLE_SEC={WRITE_THROTTLE_SEC}")
    print(f"[worker_voice_gen] idle backoff: max={IDLE_MAX_SEC}, mult={IDLE_BACKOFF_MULT}, jitter={IDLE_JITTER_SEC}")
    print(f"[worker_voice_gen] voice_gen={VOICE_GEN_SCRIPT_PATH}")

    idle_sleep = POLL_SEC  # 큐 비면 점점 늘림

    while True:
        try:
            task = claim_one(wsq)
            if not task:
                # ✅ 큐 비어있으면 점점 더 느리게(최대 IDLE_MAX_SEC) + 지터
                s = min(idle_sleep, IDLE_MAX_SEC) + random.uniform(0, IDLE_JITTER_SEC)
                time.sleep(s)
                idle_sleep = min(IDLE_MAX_SEC, idle_sleep * IDLE_BACKOFF_MULT)
                continue

            # ✅ 작업 잡으면 즉시 기본 폴링으로 복귀
            idle_sleep = POLL_SEC

            row_no = int(task["_row"])
            job_id = str(task.get("job_id", "")).strip()
            payload_raw = str(task.get("payload_json", "")).strip()
            source_row = str(task.get("source_row", "")).strip()
            source_sheet = str(task.get("source_sheet", "")).strip()

            payload: Dict[str, Any] = {}
            if payload_raw:
                try:
                    payload = json.loads(payload_raw)
                except Exception:
                    payload = {}

            # TARGET_ROW 결정 우선순위:
            # 1) payload.target_row
            # 2) payload.source_row
            # 3) queue 컬럼 source_row
            target_row = payload.get("target_row") or payload.get("source_row") or source_row
            try:
                target_row_int = int(str(target_row))
            except Exception:
                raise RuntimeError(f"target_row를 결정할 수 없습니다. payload={payload} source_row={source_row}")

            print(f"[worker_voice_gen] claim queue_row={row_no} job_id={job_id} -> target_row={target_row_int} ({source_sheet})")

            rc, out, err, elapsed = run_voice_gen_for_target(target_row_int, payload)

            result = {
                "worker_id": WORKER_ID,
                "job_id": job_id,
                "queue_row": row_no,
                "target_row": target_row_int,
                "return_code": rc,
                "elapsed_sec": round(elapsed, 3),
                "stdout_tail": _tail(out, MAX_STD_TAIL_CHARS),
                "stderr_tail": _tail(err, MAX_STD_TAIL_CHARS),
                "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
            result_json = json.dumps(result, ensure_ascii=False)

            if rc == 0:
                finish(wsq, row_no, ok=True, result_json=result_json, err="")
                print(f"[worker_voice_gen] DONE queue_row={row_no} (elapsed={elapsed:.2f}s)")
            else:
                finish(wsq, row_no, ok=False, result_json=result_json, err=f"voice_gen exit code {rc}")
                print(f"[worker_voice_gen] ERROR queue_row={row_no} rc={rc} (elapsed={elapsed:.2f}s)")

        except KeyboardInterrupt:
            print("[worker_voice_gen] interrupted by user")
            break
        except APIError as e:
            print(f"[worker_voice_gen] APIError: {e} — sleeping…")
            time.sleep(POLL_SEC * 2)
        except Exception as e:
            print(f"[worker_voice_gen] loop error: {type(e).__name__}: {e}")
            print(_tail(traceback.format_exc(), 6000))
            time.sleep(POLL_SEC * 2)


if __name__ == "__main__":
    loop()
