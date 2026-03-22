#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
inpock_upload.py

- .env 의 SPREADSHEET_LINK에 연결된 '영상다운로드' 시트(헤더 4행)에서
  'inpock업로드' == '작업 필요' 인 행을 대상으로 업로드 수행.
- 로그인: 각 행의 'inpock_ID' / 'inpock_PASSWORD' 값 사용.
- 링크: '쿠팡파트너스링크' / 제목: '키워드'
- 썸네일: '작업 완료시간' → done/YYYY-MM-DD/insta_download/insta_<다운로드파일명>.jpg
         (미존재 시 insta_<다운로드파일명>.mp4.jpg, 그리고 폴더 내 이미지 확장자 탐색 순)
- 성공 시 해당 행의 'inpock업로드' → '작업 완료'
- Google Sheets 429 대응: 개별 update_cell 금지, 배치 쓰기 + 지수 백오프 적용
- undetected-chromedriver: 매 실행 임시 프로필 사용(쿠키/캐시 초기화), 계정 전환 시 세션도 초기화
"""

import os
import re
import time
import glob
import shutil
import random
import tempfile
from typing import Optional, Dict, List

import gspread
from gspread.exceptions import APIError
from dotenv import load_dotenv

import undetected_chromedriver as uc
# from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException
)
ChromeOptions = uc.ChromeOptions
import platform
import subprocess
import shutil

# ─────────────────────────────
# 환경/시트 설정
# ─────────────────────────────
load_dotenv(dotenv_path=".env")
CREDS_PATH = os.getenv("CREDS_FILE_OHL1")
SPREADSHEET_LINK_inpock = os.getenv("SPREADSHEET_LINK_inpock")
if not CREDS_PATH or not SPREADSHEET_LINK_inpock:
    raise RuntimeError("환경변수 CREDS_FILE_OHL1 / SPREADSHEET_LINK 를 .env에 설정하세요.")

SHEET_NAME = "영상다운로드"
HEADER_ROW = 4
def get_chrome_major_version() -> Optional[int]:
    """
    로컬 설치된 Chrome의 메이저 버전(예: 141)을 반환.
    감지 실패 시 None.
    """
    try:
        system = platform.system()
        version_str = None

        if system == "Windows":
            # 우선 PATH에서 chrome.exe 탐색
            chrome_path = (
                shutil.which("chrome") or
                shutil.which("chrome.exe") or
                r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            )
            if chrome_path and os.path.isfile(chrome_path):
                out = subprocess.check_output([chrome_path, "--version"], stderr=subprocess.STDOUT, text=True)
                version_str = out.strip()
            else:
                # 레지스트리 조회(일부 환경)
                try:
                    out = subprocess.check_output(
                        r'reg query "HKLM\SOFTWARE\Google\Chrome\BLBeacon" /v version',
                        shell=True, text=True, stderr=subprocess.STDOUT
                    )
                    # 예:    version    REG_SZ    141.0.1234.56
                    m = re.search(r"version\s+REG_\w+\s+(\d+)\.", out)
                    if m:
                        return int(m.group(1))
                except Exception:
                    pass

        elif system == "Darwin":  # macOS
            candidates = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                shutil.which("google-chrome"),
                shutil.which("chrome"),
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    out = subprocess.check_output([c, "--version"], stderr=subprocess.STDOUT, text=True)
                    version_str = out.strip()
                    break

        else:  # Linux
            for cmd in ["google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"]:
                path = shutil.which(cmd)
                if path:
                    out = subprocess.check_output([path, "--version"], stderr=subprocess.STDOUT, text=True)
                    version_str = out.strip()
                    break

        if version_str:
            # 예: "Google Chrome 141.0.1234.56" 또는 "Chromium 141.0.XXXX.XX"
            m = re.search(r"(\d+)\.", version_str)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None

# Inpock URL
INPOCK_LOGIN_URL = "https://link.inpock.co.kr/user/login"
INPOCK_ADMIN_URL = "https://link.inpock.co.kr/admin/block/link/post"

# XPaths (현 UI 기준)
XPATH_ID_INPUT = '//*[@id="layout--default"]/div[2]/section/form/div/div[1]/div[2]/div/div/input'
XPATH_PW_INPUT = '//*[@id="layout--default"]/div[2]/section/form/div/div[2]/div[2]/div/div/input'
XPATH_LOGIN_BTN = '//*[@id="layout--default"]/div[2]/section/footer/button[1]/div'

XPATH_LINK_INPUT = '//*[@id="layout--default"]/div/div[2]/main/div/div[2]/div[1]/div/section[1]/div[4]/div[2]/div/div/input'
XPATH_KEYWORD_INPUT = '//*[@id="layout--default"]/div/div[2]/main/div/div[2]/div[1]/div/section[1]/div[5]/div[1]/div[2]/textarea'
XPATH_UPLOAD_CLICK_TARGET = '//*[@id="layout--default"]/div/div[2]/main/div/div[2]/div[1]/div/section[1]/div[6]/div[2]/div[1]/div/div/div/div/div/div[2]/div'
XPATH_TOP_SAVE_BTN = '//*[@id="layout--default"]/div/div[2]/main/div/div[1]/div[4]/div/button[2]/div/div/span'
XPATH_FINAL_CONFIRM_BTN = '//*[@id="layout--default"]/div/div[2]/div/div/section/button'

# 시트 컬럼명
COL_STATE   = "inpock업로드"      # 작업 상태(작업 필요/작업 완료)
COL_LINK    = "쿠팡파트너스링크"   # 링크
COL_KEYWORD = "키워드"            # 제목
COL_DONE_AT = "작업 완료시간"       # 예: 2025/09/02 13:05
COL_DL_NAME = "다운로드파일명"       # 파일명(확장자 포함 가능)
COL_ID      = "inpock_ID"        # 로그인 ID
COL_PW      = "inpock_PASSWORD"  # 로그인 PW

# 상태 값
STATE_TARGET = "작업 시작"
STATE_DONE   = "작업 완료"

# 선택 컬럼(있으면 에러 기록)
COL_NOTE = "작업 비고"
COL_SEL  = "작업 선택"

# 배치 쓰기 플러시 기준
FLUSH_EVERY = 50

# ─────────────────────────────
# 공통 유틸
# ─────────────────────────────
def safe_get_idx(header: list, col_name: str) -> Optional[int]:
    return (header.index(col_name) + 1) if col_name in header else None

def wait_visible(drv, xpath: str, timeout: int = 20):
    return WebDriverWait(drv, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))

def wait_clickable(drv, xpath: str, timeout: int = 20):
    return WebDriverWait(drv, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))

def find_input_type_file(drv) -> Optional[object]:
    try:
        return drv.find_element(By.CSS_SELECTOR, "input[type='file']")
    except NoSuchElementException:
        return None

def sanitize_path(p: str) -> str:
    return os.path.abspath(os.path.expandvars((p or "").strip()))

def parse_done_date_folder(done_at: str) -> str:
    """'2025/09/02 13:05' → '2025-09-02' (실패 시 오늘 날짜)"""
    done_at = (done_at or "").strip()
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            import datetime
            dt = datetime.datetime.strptime(done_at, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d")

def resolve_thumbnail_path(done_at: str, dl_name: str) -> Optional[str]:
    """
    done/<YYYY-MM-DD>/insta_download/insta_<다운로드파일명>.jpg 를 최우선으로 찾고,
    없으면 insta_<다운로드파일명>.mp4.jpg, 그리고 폴더 내 이미지 확장자 탐색.
    """
    date_folder = parse_done_date_folder(done_at)
    base_dir = os.path.join("done", date_folder, "insta_download")
    os.makedirs(base_dir, exist_ok=True)

    base = f"insta_{dl_name}".strip()
    candidates = [
        os.path.join(base_dir, f"{base}.jpg"),
        os.path.join(base_dir, f"{base}.mp4.jpg"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return os.path.abspath(cand)

    for pat in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        files = glob.glob(os.path.join(base_dir, pat))
        if files:
            return os.path.abspath(files[0])

    return None

# ─────────────────────────────
# gspread 안전 배치 업데이트(429/5xx 백오프)
# ─────────────────────────────
def safe_batch_update(ws, batch: List[Dict], max_attempts: int = 6, base: float = 1.5, max_sleep: float = 20.0):
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
                print(f"[경고] Sheets 쓰기 백오프 재시도 {attempt}/{max_attempts} ({sleep_s:.1f}s): {msg[:120]}")
                time.sleep(sleep_s)
                continue
            raise

# ─────────────────────────────
# 브라우저 초기화 & 로그인
# ─────────────────────────────
def launch_browser() -> uc.Chrome:
    tmp_profile = tempfile.mkdtemp(prefix="uc_profile_")

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={tmp_profile}")
    options.add_argument("--start-maximized")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # ✅ uc에게 전부 맡김 (가장 안정)
    driver = uc.Chrome(
        options=options,
        use_subprocess=False
    )

    driver.set_page_load_timeout(60)

    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
    except Exception:
        pass

    driver._tmp_profile_dir = tmp_profile
    return driver

def login_inpock(driver: uc.Chrome, user_id: str, user_pw: str):
    driver.get(INPOCK_LOGIN_URL)
    id_input = wait_visible(driver, XPATH_ID_INPUT, 30)
    pw_input = wait_visible(driver, XPATH_PW_INPUT, 30)
    id_input.clear(); id_input.send_keys(user_id)
    pw_input.clear(); pw_input.send_keys(user_pw)
    btn = wait_clickable(driver, XPATH_LOGIN_BTN, 20)
    btn.click()
    WebDriverWait(driver, 30).until(lambda d: "user/login" not in d.current_url)
    time.sleep(1)

# ─────────────────────────────
# 게시 블록 작성 루틴 (단일 행)
# ─────────────────────────────
def process_row(driver: uc.Chrome, link_val: str, keyword_val: str, thumb_path: str) -> bool:
    driver.get(INPOCK_ADMIN_URL)

    # 링크/키워드 입력
    link_input = wait_visible(driver, XPATH_LINK_INPUT, 30)
    link_input.clear(); link_input.send_keys(link_val)

    keyword_input = wait_visible(driver, XPATH_KEYWORD_INPUT, 30)
    keyword_input.clear(); keyword_input.send_keys(keyword_val)

    # 업로드 영역 클릭
    upload_target = wait_clickable(driver, XPATH_UPLOAD_CLICK_TARGET, 30)
    upload_target.click(); time.sleep(0.5)

    file_input = find_input_type_file(driver)
    if not file_input:
        upload_target.click(); time.sleep(0.5)
        file_input = find_input_type_file(driver)
        if not file_input:
            print("[경고] 파일 업로드 입력 요소를 찾지 못했습니다.")
            return False

    file_input.send_keys(thumb_path)

    # 저장/확인
    save_btn = wait_clickable(driver, XPATH_TOP_SAVE_BTN, 30)
    save_btn.click(); time.sleep(0.8)

    final_btn = wait_clickable(driver, XPATH_FINAL_CONFIRM_BTN, 30)
    final_btn.click(); time.sleep(1.5)
    return True

# ─────────────────────────────
# 메인
# ─────────────────────────────
def main():
    # 시트 준비
    gc = gspread.service_account(filename=CREDS_PATH)
    sh = gc.open_by_url(SPREADSHEET_LINK_inpock)
    ws = sh.worksheet(SHEET_NAME)

    header = ws.row_values(HEADER_ROW)
    idx_state   = safe_get_idx(header, COL_STATE)
    idx_link    = safe_get_idx(header, COL_LINK)
    idx_keyword = safe_get_idx(header, COL_KEYWORD)
    idx_done_at = safe_get_idx(header, COL_DONE_AT)
    idx_dl_name = safe_get_idx(header, COL_DL_NAME)
    idx_id      = safe_get_idx(header, COL_ID)
    idx_pw      = safe_get_idx(header, COL_PW)
    idx_note    = safe_get_idx(header, COL_NOTE) if COL_NOTE in header else None
    idx_sel     = safe_get_idx(header, COL_SEL)  if COL_SEL in header  else None

    all_rows = ws.get_all_values()

    driver = launch_browser()
    current_cred = (None, None)  # (id, pw)

    # 배치 쓰기 버퍼
    pending_updates: List[Dict] = []  # 성공 시 상태 마킹
    pending_errors:  List[Dict] = []  # 에러 비고/상태

    try:
        # 5행부터 순회
        for row_num, row in enumerate(all_rows[HEADER_ROW:], start=HEADER_ROW + 1):
            try:
                state_val   = (row[idx_state   - 1] if idx_state   and len(row) >= idx_state   else "").strip()
                link_val    = (row[idx_link    - 1] if idx_link    and len(row) >= idx_link    else "").strip()
                keyword_val = (row[idx_keyword - 1] if idx_keyword and len(row) >= idx_keyword else "").strip()
                done_at     = (row[idx_done_at - 1] if idx_done_at and len(row) >= idx_done_at else "").strip()
                dl_name     = (row[idx_dl_name - 1] if idx_dl_name and len(row) >= idx_dl_name else "").strip()
                user_id     = (row[idx_id      - 1] if idx_id      and len(row) >= idx_id      else "").strip()
                user_pw     = (row[idx_pw      - 1] if idx_pw      and len(row) >= idx_pw      else "").strip()

                if state_val != STATE_TARGET:
                    continue
                if not (link_val and keyword_val and done_at and dl_name and user_id and user_pw):
                    print(f"[건너뜀] 필수값 누락 (행 {row_num})")
                    continue

                # 썸네일 경로 해석
                thumb_path = resolve_thumbnail_path(done_at, dl_name)
                if not thumb_path or not os.path.isfile(thumb_path):
                    print(f"[건너뜀] 썸네일 파일 없음 (행 {row_num}) / {thumb_path or '(None)'}")
                    continue

                # 로그인(자격 증명이 바뀌면 세션 초기화 후 재로그인)
                if (user_id, user_pw) != current_cred:
                    try:
                        # 이전 세션 흔적 제거
                        try:
                            driver.execute_cdp_cmd("Network.enable", {})
                            driver.execute_cdp_cmd("Network.clearBrowserCache", {})
                            driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
                            try:
                                driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                            except Exception:
                                pass
                        except Exception:
                            pass

                        login_inpock(driver, user_id, user_pw)
                        current_cred = (user_id, user_pw)
                    except Exception as e:
                        print(f"[로그인 실패] 행 {row_num}: {e}")
                        note_txt = f"[단계] 로그인\n[에러] {type(e).__name__}: {e}"
                        if idx_note:
                            pending_errors.append({
                                "range": gspread.utils.rowcol_to_a1(row_num, idx_note),
                                "values": [[note_txt]],
                            })
                        if idx_sel:
                            pending_errors.append({
                                "range": gspread.utils.rowcol_to_a1(row_num, idx_sel),
                                "values": [["작업 중 에러"]],
                            })
                        # 주기적 플러시
                        if len(pending_errors) >= FLUSH_EVERY:
                            safe_batch_update(ws, pending_errors); pending_errors.clear()
                        continue

                # 업로드
                ok = process_row(driver, link_val, keyword_val, thumb_path)
                if ok:
                    if idx_state:
                        pending_updates.append({
                            "range": gspread.utils.rowcol_to_a1(row_num, idx_state),
                            "values": [[STATE_DONE]],
                        })
                        if len(pending_updates) >= FLUSH_EVERY:
                            safe_batch_update(ws, pending_updates); pending_updates.clear()
                    print(f"[완료] 행 {row_num} 처리 완료")
                else:
                    print(f"[실패] 행 {row_num} 처리 실패")
                    note_txt = "[단계] 업로드\n[에러] 업로드 실패(원인 미상)"
                    if idx_note:
                        pending_errors.append({
                            "range": gspread.utils.rowcol_to_a1(row_num, idx_note),
                            "values": [[note_txt]],
                        })
                    if idx_sel:
                        pending_errors.append({
                            "range": gspread.utils.rowcol_to_a1(row_num, idx_sel),
                            "values": [["작업 중 에러"]],
                        })
                    if len(pending_errors) >= FLUSH_EVERY:
                        safe_batch_update(ws, pending_errors); pending_errors.clear()

            except Exception as e:
                print(f"[예외] 행 {row_num} 처리 중 오류: {e}")
                note_txt = f"[단계] 업로드\n[에러] {type(e).__name__}: {e}"
                if idx_note:
                    pending_errors.append({
                        "range": gspread.utils.rowcol_to_a1(row_num, idx_note),
                        "values": [[note_txt]],
                    })
                if idx_sel:
                    pending_errors.append({
                        "range": gspread.utils.rowcol_to_a1(row_num, idx_sel),
                        "values": [["작업 중 에러"]],
                    })
                if len(pending_errors) >= FLUSH_EVERY:
                    safe_batch_update(ws, pending_errors); pending_errors.clear()
                continue

        # 루프 종료 후 잔여 배치 플러시
        if pending_errors:
            safe_batch_update(ws, pending_errors); pending_errors.clear()
        if pending_updates:
            safe_batch_update(ws, pending_updates); pending_updates.clear()

    finally:
        # 브라우저 종료 + 임시 프로필 디렉터리 정리
        try:
            driver.quit()
        except Exception:
            pass
        try:
            if hasattr(driver, "_tmp_profile_dir") and os.path.isdir(driver._tmp_profile_dir):
                shutil.rmtree(driver._tmp_profile_dir, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    main()
