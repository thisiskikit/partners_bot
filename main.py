#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

# 단계별 실행 모듈
import video_downloader as vd
import partners_link as pl
import tts_ge as tts
import inpock_upload as iu  # 단독 실행 모듈

# ── Sheets 업데이트용
import os
import random
import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

# ── Tkinter UI
import tkinter as tk
from tkinter import ttk, messagebox

# ── typing (3.9 이하 호환)
from typing import Optional, Set, List, Dict
import send_email as se

SHEET_NAME = "영상다운로드"
HEADER_ROW = 4

# ─────────────────────────────────────────
# 공용 로깽
# ─────────────────────────────────────────
class TextboxHandler(logging.Handler):
    """tk.Text 위젯으로 로그를 보냅니다."""
    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text = text_widget

    def emit(self, record):
        msg = self.format(record)
        def _append():
            self.text.insert(tk.END, msg + "\n")
            self.text.see(tk.END)
        self.text.after(0, _append)

def setup_logging(level: str = "INFO", text_widget: Optional[tk.Text] = None):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(lvl)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(lvl)
    sh.setFormatter(fmt)
    logging.getLogger().addHandler(sh)

    if text_widget is not None:
        th = TextboxHandler(text_widget)
        th.setLevel(lvl)
        th.setFormatter(fmt)
        logging.getLogger().addHandler(th)

    # 🔇 noisy 서드파티 로거 억제
    for name in [
        "httpx","httpcore","openai","urllib3","requests",
        "googleapiclient.discovery","google.auth",
    ]:
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        lg.propagate = False

# ─────────────────────────────────────────
# 일시중지 제어 (협력적 pause)
# ─────────────────────────────────────────
pause_event = threading.Event()  # set() = 일시중지 상태

def pause_gate(log: Optional[logging.Logger] = None, ui_status_setter=None):
    """일시중지 상태면 해제될 때까지 대기."""
    while pause_event.is_set():
        if log:
            log.debug("일시중지 상태 - 재개를 기다리는 중…")
        if ui_status_setter:
            ui_status_setter("일시중지 중…")
        time.sleep(0.2)
_read_last_ts = 0.0  # 프로세스 전역 최소 간격 스로틀용

def _throttle_reads(min_interval=0.35):
    """연속 read 사이 최소 간격 확보(분당 요청 수 완화)."""
    import time as _t
    global _read_last_ts
    now = _t.monotonic()
    dt = now - _read_last_ts
    if dt < min_interval:
        _t.sleep(min_interval - dt)
    _read_last_ts = _t.monotonic()

def _is_transient_api_error(e: Exception) -> bool:
    msg = str(e)
    return any(code in msg for code in ("429", "500", "502", "503", "504"))

def safe_batch_get(ws, ranges, *, max_attempts=7, base=1.7, max_sleep=60.0, ui_status_setter=None, log=None):
    """
    ws.batch_get(ranges)를 429/5xx에서 지수 백오프(+지터)로 재시도.
    - 호출 간 최소 간격(throttle)로 분당 요청수 완화
    """
    import random, time
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.batch_get(ranges)
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            if ui_status_setter:
                ui_status_setter(f"시트 읽기 대기 중… 재시도 {attempt}/{max_attempts} (~{sleep_s:.1f}s)")
            if log:
                log.warning("Sheets 읽기 백오프 %d/%d (%.1fs): %s", attempt, max_attempts, sleep_s, str(e)[:140])
            time.sleep(sleep_s)

def safe_row_values(ws, row, *, max_attempts=7, base=1.7, max_sleep=60.0):
    """ws.row_values(row)를 safe_batch_get로 래핑."""
    col_count = ws.col_count or 1000  # 대략적 상한
    start = gspread.utils.rowcol_to_a1(row, 1)
    end   = gspread.utils.rowcol_to_a1(row, col_count)
    res = safe_batch_get(ws, [f"{start}:{end}"])
    return res[0][0] if res and res[0] else []

def safe_get_all_values(ws, *, max_attempts=7, base=1.7, max_sleep=60.0):
    """
    ws.get_all_values() 대체(큰 시트는 비추). 꼭 필요할 때만 사용.
    내부는 batch_get('A1:Z' 스타일)로 래핑 필요시 구현 확장 가능.
    """
    # 최소: throttle + 재시도
    import time as _t, random
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.get_all_values()
        except APIError as e:
            if not _is_transient_api_error(e) or attempt >= max_attempts:
                raise
            sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
            _t.sleep(sleep_s)

# ─────────────────────────────────────────
# Sheets 공통: 열 인덱싱/접속
# ─────────────────────────────────────────
def _open_sheet():
    link = os.getenv("SPREADSHEET_LINK")
    cred = os.getenv("CREDS_FILE_OHL2")
    if not (link and cred):
        raise RuntimeError("SPREADSHEET_LINK / CREDS_FILE_OHL2 를 .env 에 설정하세요.")
    gc = gspread.authorize(
        Credentials.from_service_account_file(
            cred, scopes=["https://www.googleapis.com/auth/spreadsheets",
                          "https://www.googleapis.com/auth/drive"]
        )
    )
    sh = gc.open_by_url(link)
    return sh.worksheet(SHEET_NAME)

def _col_index_map(ws):
    header = safe_row_values(ws, HEADER_ROW)  # 변경
    return {name: (header.index(name) + 1) for name in header}

# ─────────────────────────────────────────
# 429 대응: 안전 배치 업데이트
# ─────────────────────────────────────────
def safe_batch_update(ws, batch, max_attempts=6, base=1.5, max_sleep=20.0):
    """429/5xx에서 지수 백오프(+지터)로 재시도."""
    if not batch:
        return
    for attempt in range(1, max_attempts + 1):
        try:
            ws.batch_update(batch)
            return
        except APIError as e:
            msg = str(e)
            transient = any(code in msg for code in ("429", "500", "502", "503", "504"))
            if transient and attempt < max_attempts:
                sleep_s = min(max_sleep, (base ** (attempt - 1))) + random.uniform(0, 0.5)
                logging.getLogger("main").warning("Sheets 쓰기 백오프 재시도 %d/%d (%.1fs): %s",
                                                  attempt, max_attempts, sleep_s, msg[:120])
                time.sleep(sleep_s)
                continue
            raise

# ─────────────────────────────────────────
# 완료 마킹: 배치/청크 + 백오프
# ─────────────────────────────────────────
def mark_rows_done(rows):
    if not rows:
        return
    ws = _open_sheet()
    idx = _col_index_map(ws)

    ts = datetime.now().strftime("%Y/%m/%d %H:%M")
    rows = sorted(set(rows))

    # 너무 많은 요청 방지: 100행 단위로 쪼개서 커밋
    CHUNK = 300
    for i in range(0, len(rows), CHUNK):
        sub = rows[i:i+CHUNK]
        batch = []
        for r in sub:
            if "작업 선택" in idx:
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(r, idx["작업 선택"]),
                    "values": [["작업 완료"]],
                })
            if "작업 완료시간" in idx:
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(r, idx["작업 완료시간"]),
                    "values": [[ts]],
                })
        safe_batch_update(ws, batch)

# ─────────────────────────────────────────
# “거의 완료” 판정 (읽기 1회, 셀 호출 없음)
# ─────────────────────────────────────────
def find_rows_to_mark_fallback():
    ws = _open_sheet()
    idx = _col_index_map(ws)

    need_names = ["다운로드파일명", "스크립트"]
    for c in need_names:
        if c not in idx:
            return set()

    # 읽을 열 집합 구성 (존재하는 것만)
    col_names = ["작업 선택", "다운로드파일명", "스크립트", "인스타글내용", "영상길이"]
    cols = [(name, idx[name]) for name in col_names if name in idx]

    start = HEADER_ROW + 1
    end = ws.row_count
    ranges = []
    for _, c in cols:
        a1 = f"{gspread.utils.rowcol_to_a1(start, c)}:{gspread.utils.rowcol_to_a1(end, c)}"
        ranges.append(a1)

    # 한 번의 batch_get으로 필요한 열만 안전하게 읽기
    res = safe_batch_get(ws, ranges, log=logging.getLogger("main")) or []
    # res[i] 는 해당 열의 2차원 값 리스트

    # 열명 -> 1차원 리스트 매핑
    col_map: Dict[str, List[str]] = {}
    for (name, _), col_vals in zip(cols, res):
        # gspread batch_get는 [[row1_val],[row2_val],...] 형태
        col_map[name] = [(r[0] if r else "") for r in col_vals]

    n = max(len(v) for v in col_map.values()) if col_map else 0

    def gv(name, i):
        arr = col_map.get(name, [])
        return (arr[i] if i < len(arr) else "").strip()

    to_mark = set()
    for i in range(n):
        cur_sel = gv("작업 선택", i)
        if cur_sel == "작업 완료":
            continue

        fname  = gv("다운로드파일명", i)
        script = gv("스크립트", i)
        if not fname or not script:
            continue

        insta_ok = gv("인스타글내용", i) if "인스타글내용" in col_map else ""
        len_ok   = gv("영상길이", i)     if "영상길이" in col_map     else ""
        if ("인스타글내용" in col_map or "영상길이" in col_map) and (not insta_ok and not len_ok):
            continue

        # 시트 실제 행번호(1-based)
        to_mark.add(start + i)

    return to_mark

# ─────────────────────────────────────────
# 신규: 상태 전환 유틸
# ─────────────────────────────────────────
def _get_rows_by_selection(value: str) -> List[int]:
    """'작업 선택' 값이 value 인 행 목록(1-based) 반환."""
    ws = _open_sheet()
    idx = _col_index_map(ws)
    if "작업 선택" not in idx:
        return []
    start = HEADER_ROW + 1
    end = ws.row_count
    rng = f"{gspread.utils.rowcol_to_a1(start, idx['작업 선택'])}:{gspread.utils.rowcol_to_a1(end, idx['작업 선택'])}"

    res = safe_batch_get(ws, [rng], log=logging.getLogger("main"))
    col_vals = res[0] if res else []

    rows = []
    for i, row in enumerate(col_vals):
        if row and (row[0] or "").strip() == value:
            rows.append(start + i)
    return rows

def _set_selection(rows: List[int], new_value: str, also_set_done_time: bool = False):
    """지정 행들의 '작업 선택' 값을 일괄 변경(필요 시 작업 완료시간도)."""
    if not rows:
        return
    ws = _open_sheet()
    idx = _col_index_map(ws)
    batch = []
    for r in rows:
        if "작업 선택" in idx:
            batch.append({
                "range": gspread.utils.rowcol_to_a1(r, idx["작업 선택"]),
                "values": [[new_value]]
            })
        if also_set_done_time and "작업 완료시간" in idx:
            ts = datetime.now().strftime("%Y/%m/%d %H:%M")
            batch.append({
                "range": gspread.utils.rowcol_to_a1(r, idx["작업 완료시간"]),
                "values": [[ts]]
            })
    safe_batch_update(ws, batch)

def _log_append(rows: List[int], message: str):
    if not rows:
        return
    ws = _open_sheet()
    idx = _col_index_map(ws)
    if "작업로그" not in idx:
        return
    batch = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        try:
            prev = ws.cell(r, idx["작업로그"]).value or ""
        except Exception:
            prev = ""
        newmsg = (prev + "\n" if prev else "") + f"{ts} - {message}"
        batch.append({
            "range": gspread.utils.rowcol_to_a1(r, idx["작업로그"]),
            "values": [[newmsg]]
        })
    safe_batch_update(ws, batch)

# ─────────────────────────────────────────
# 단계 실행기 (신규 버튼용)
# ─────────────────────────────────────────
def run_link_video_download_only(log: logging.Logger, ui_status_setter=None):
    """'영상다운로드' 행만 대상으로 vd.process 실행 후 성공행을 '스크립트생성'으로 전환."""
    pause_gate(log, ui_status_setter)
    targets = _get_rows_by_selection("영상다운로드")
    if not targets:
        log.info("대상(영상다운로드) 행이 없습니다.")
        return

    log.info("▶ 링크영상다운로드: 대상 행 수=%d", len(targets))
    processed: Set[int] = set()
    try:
        # 모듈이 target_rows 인자를 지원하면 사용
        try:
            rows = vd.process(target_rows=targets)
            if rows:
                processed.update(rows)
        except TypeError:
            # 폴백: 전체 실행 후 교집합만 반영
            rows = vd.process()
            if rows:
                processed.update(set(rows).intersection(set(targets)))
    except Exception as e:
        log.exception("video_downloader 실행 오류: %s", e)

    if processed:
        _set_selection(sorted(processed), "스크립트생성")
        _log_append(sorted(processed), "영상 다운로드 완료 → 스크립트생성으로 전환")
        log.info("✅ 링크영상다운로드 완료 (전환 %d행)", len(processed))
    else:
        log.info("처리된 행이 없습니다.")


def run_tts_and_email_only(log: logging.Logger, ui_status_setter=None):
    """'TTS생성' 행만 대상으로 TTS → 이메일 발송 → '작업완료' 전환."""
    pause_gate(log, ui_status_setter)
    targets = _get_rows_by_selection("TTS생성")
    if not targets:
        log.info("대상(TTS생성) 행이 없습니다.")
        return

    log.info("▶ 목소리_TTS생성(+이메일): 대상 행 수=%d", len(targets))
    processed: Set[int] = set()

    # 1) TTS
    try:
        try:
            rows = tts.process(target_rows=targets)
            if rows:
                processed.update(rows)
        except TypeError:
            rows = tts.process()
            if rows:
                processed.update(set(rows).intersection(set(targets)))
    except Exception as e:
        log.exception("tts_ge 실행 오류: %s", e)

    # 2) 이메일
    try:
        # processed가 있으면 그 행만, 없으면 '이메일발송' 상태 전체 대상
        email_targets = sorted(processed) if processed else None
        res = se.run(target_rows=email_targets)
        logging.getLogger("main").info("✉️ 이메일 전송 완료 (sent=%d, skipped=%d)",
                                       res.get("sent",0), res.get("skipped",0))
    except Exception as e:
        log.exception("send_email 실행 오류: %s", e)

    # 3) 완료 전환은 send_email.run()의 성공 행만 처리(오탐 완료 마킹 방지)
    if processed:
        _log_append(sorted(processed), "TTS 처리 완료 (작업완료 전환은 이메일 전송 성공 시 수행)")
        log.info("✅ 목소리_TTS생성(+이메일) 완료 (TTS 처리 %d행)", len(processed))
    else:
        log.info("ℹ️ TTS 대상이 없어 후속 완료 전환은 생략")

# ─────────────────────────────────────────
# 기존 통합 파이프라인 (유지)
# ─────────────────────────────────────────
def run_video_pipeline(log: logging.Logger, ui_status_setter=None):
    tts_processed = set()
    email_sent = 0
    email_skipped = 0

    # ── (A) 영상다운로드 단계: '영상다운로드' 행만 타겟팅 ─────────────────
    pause_gate(log, ui_status_setter)
    log.info("▶ Stage: video_downloader")
    try:
        targets = _get_rows_by_selection("영상다운로드")
        if not targets:
            log.info("대상(영상다운로드) 행이 없습니다. video_downloader 생략합니다.")
            rows = []
        else:
            try:
                # 모듈이 target_rows 인자를 지원하면 사용
                rows = vd.process(target_rows=targets)
            except TypeError:
                # 폴백: 전체 실행 후 교집합만 반영
                rows = vd.process()
                if rows:
                    rows = list(set(rows) & set(targets))
    except Exception as e:
        log.exception("video_downloader 실행 중 오류: %s", e)

    # ── (B) 이후 단계는 기존대로 ───────────────────────────────────────
    pause_gate(log, ui_status_setter)
    log.info("▶ Stage: partners_link")
    try:
        pl.process(force=False)
    except Exception as e:
        log.exception("partners_link 실행 중 오류: %s", e)

    pause_gate(log, ui_status_setter)
    log.info("▶ Stage: tts_ge")
    try:
        rows = tts.process()
        if rows:
            tts_processed.update(rows)
    except Exception as e:
        log.exception("tts_ge 실행 중 오류: %s", e)

    # 이메일 단계
    pause_gate(log, ui_status_setter)
    log.info("▶ Stage: send_email")
    try:
        res = se.run(target_rows=tts_processed if tts_processed else None)
        email_sent = res.get("sent", 0)
        email_skipped = res.get("skipped", 0)
        log.info("✉️ 이메일 전송 완료 (sent=%d, skipped=%d)", email_sent, email_skipped)
    except Exception as e:
        log.exception("send_email 실행 중 오류: %s", e)

    log.info(
        "✅ 영상다운로드 파이프라인 완료 (tts_ok=%d, email_sent=%d, email_skipped=%d)",
        len(tts_processed), email_sent, email_skipped
    )
def run_inpock_upload(log: logging.Logger, ui_status_setter=None):
    """inpock_upload.py 실행 (mid-run 일시중지 불가)"""
    log.info("▶ Stage: run_inpock_upload")
    pause_gate(log, ui_status_setter)
    try:
        iu.main()
        log.info("✅ 인포크링크업로드 실행 완료")
    except Exception as e:
        log.exception("인포크링크업로드 실행 중 오류: %s", e)
    pause_gate(log, ui_status_setter)

# ─────────────────────────────────────────
# Tk 앱 (신규 버튼 추가)
# ─────────────────────────────────────────
class LauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("영상 자동화 오케스트레이터")
        self.root.geometry("1100x680")

        # 상단 컨트롤 프레임
        top = ttk.Frame(root, padding=12)
        top.pack(side=tk.TOP, fill=tk.X)

        # 기존 버튼
        self.btn_vd   = ttk.Button(top, text="🎬  영상다운로드 실행(통합)", command=self.start_vd)
        self.btn_inpk = ttk.Button(top, text="🔗  인포크링크업로드 실행", command=self.start_inpock)

        self.btn_vd.pack(side=tk.LEFT, padx=6)
        self.btn_inpk.pack(side=tk.LEFT, padx=6)

        ttk.Separator(top, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # 🔽 신규 3단계 버튼
        self.btn_link_dl = ttk.Button(top, text="📥  링크영상다운로드", command=self.start_link_download_only)
        self.btn_tts     = ttk.Button(top, text="🎤  목소리_TTS생성(이메일 포함)", command=self.start_tts_and_email_only)

        self.btn_link_dl.pack(side=tk.LEFT, padx=6)
        self.btn_tts.pack(side=tk.LEFT, padx=6)

        ttk.Separator(top, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # 일시중지/재개 토글 버튼
        self.pause_on = tk.BooleanVar(value=False)
        self.btn_pause = ttk.Button(top, text="⏸  일시중지", command=self.toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=10)

        ttk.Label(top, text="로그 레벨:").pack(side=tk.LEFT, padx=(16,2))
        self.level_var = tk.StringVar(value="INFO")
        level_cb = ttk.Combobox(top, textvariable=self.level_var,
                                values=["DEBUG","INFO","WARNING","ERROR"],
                                width=10, state="readonly")
        level_cb.bind("<<ComboboxSelected>>", self.on_level_change)
        level_cb.pack(side=tk.LEFT, padx=4)

        # 로그 텍스트
        mid = ttk.Frame(root, padding=(12, 0, 12, 12))
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.text = tk.Text(mid, wrap="word", height=22)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll = ttk.Scrollbar(mid, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 하단 상태바
        bottom = ttk.Frame(root, padding=8)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = tk.StringVar(value="대기 중")
        ttk.Label(bottom, textvariable=self.status).pack(side=tk.LEFT)

        # 로깅 초기화
        setup_logging(level="INFO", text_widget=self.text)
        self.log = logging.getLogger("launcher")

    def on_level_change(self, _evt=None):
        setup_logging(level=self.level_var.get(), text_widget=self.text)
        self.log = logging.getLogger("launcher")
        self.log.info("로그 레벨을 %s 로 변경했습니다.", self.level_var.get())

    def toggle_pause(self):
        if not self.pause_on.get():
            pause_event.set()
            self.pause_on.set(True)
            self.btn_pause.config(text="▶  재개")
            self.status.set("일시중지 중…")
            self.log.info("⏸ 일시중지되었습니다. 재개를 누르면 계속 진행합니다.")
        else:
            pause_event.clear()
            self.pause_on.set(False)
            self.btn_pause.config(text="⏸  일시중지")
            self.status.set("진행 중…")
            self.log.info("▶ 재개되었습니다.")

    def _run_in_thread(self, target):
        def runner():
            try:
                target()
            except Exception as e:
                self.log.exception("실행 중 예외: %s", e)
            finally:
                self.status.set("대기 중")
        t = threading.Thread(target=runner, daemon=True)
        t.start()

    # 기존 버튼 핸들러
    def start_vd(self):
        self.status.set("영상다운로드(통합 파이프라인) 실행 중…")
        self._run_in_thread(lambda: run_video_pipeline(self.log, self.status.set))

    def start_inpock(self):
        self.status.set("인포크링크업로드 실행 중…")
        self._run_in_thread(lambda: run_inpock_upload(self.log, self.status.set))

    # 신규 버튼 핸들러
    def start_link_download_only(self):
        self.status.set("링크영상다운로드 실행 중…")
        self._run_in_thread(lambda: run_link_video_download_only(self.log, self.status.set))


    def start_tts_and_email_only(self):
        self.status.set("목소리_TTS생성(+이메일) 실행 중…")
        self._run_in_thread(lambda: run_tts_and_email_only(self.log, self.status.set))

# ─────────────────────────────────────────
# 진입점 (CLI/GUI)
# ─────────────────────────────────────────
def parse_args():
    ap = argparse.ArgumentParser(description="영상 자동화 오케스트레이터 (GUI)")
    ap.add_argument("--no-gui", action="store_true", help="GUI 없이 기존 파이프라인 실행")
    ap.add_argument("--log-level", default="INFO", help="GUI 미사용 시 로그 레벨")
    ap.add_argument("--stage", choices=["vd", "link", "tts", "all"], default="all",
                    help="--no-gui 모드에서 실행할 단계")
    ap.add_argument("--force-link", action="store_true", help="--no-gui 모드에서 링크 강제 덮어쓰기")
    return ap.parse_args()

def main_cli(args):
    setup_logging(args.log_level)
    log = logging.getLogger("main-cli")

    tts_rows = set()
    email_sent = 0
    email_skipped = 0
    pause_gate(log)
    if args.stage in ("vd", "all"):
        log.info("▶ Stage: video_downloader")
        vd.process()

    pause_gate(log)
    if args.stage in ("link", "all"):
        log.info("▶ Stage: partners_link")
        pl.process(force=args.force_link)

    pause_gate(log)
    if args.stage in ("tts", "all"):
        log.info("▶ Stage: tts_ge")
        rows = tts.process()
        if rows:
            tts_rows.update(rows)

    # 이메일 단계
    pause_gate(log)
    if args.stage in ("all",):
        log.info("▶ Stage: send_email")
        try:
            res = se.run(target_rows=tts_rows if tts_rows else None)
            email_sent = res.get("sent", 0)
            email_skipped = res.get("skipped", 0)
            log.info("✉️ 이메일 전송 완료 (sent=%d, skipped=%d)", email_sent, email_skipped)
        except Exception as e:
            log.exception("send_email 실행 중 오류: %s", e)

    log.info(
        "✅ Done. (tts_ok=%d, email_sent=%d, email_skipped=%d)",
        len(tts_rows), email_sent, email_skipped
    )

def main():
    load_dotenv()
    args = parse_args()
    if args.no_gui:
        main_cli(args)
        return

    root = tk.Tk()
    # ttk 폰트 살짝 키우기
    try:
        from tkinter import font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10)
    except Exception:
        pass

    app = LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
