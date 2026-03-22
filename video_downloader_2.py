# video_downloader.py
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import random
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import traceback
import shutil
import requests
from yt_dlp import YoutubeDL
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

from openai import OpenAI
import importlib

# ──────────────────────────────────────────────────────────────
# 외부 모듈(script_gen) 주입
# ──────────────────────────────────────────────────────────────
try:
    script_gen = importlib.import_module("script_gen")
except Exception as e:
    raise RuntimeError("script_gen 모듈을 import 할 수 없습니다. 같은 폴더에 script_gen.py가 있는지 확인하세요.") from e

# ──────────────────────────────────────────────────────────────
# 환경설정
# ──────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=".env")

SPREADSHEET_LINK = os.getenv("SPREADSHEET_LINK")
if not SPREADSHEET_LINK:
    raise RuntimeError("환경변수 SPREADSHEET_LINK 가 설정되지 않았습니다(.env).")

CREDS_FILE = os.getenv("CREDS_FILE_OHL1")
if not CREDS_FILE:
    raise RuntimeError("환경변수 CREDS_FILE_OHL1 가 설정되지 않았습니다(.env).")

OPENAI_API_KEY = os.getenv("openai.api_key")
if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 openai.api_key 가 설정되지 않았습니다(.env).")

SHEET_NAME = "영상다운로드"
HEADER_ROW = 4

# OpenAI 클라이언트 주입(하드코딩 키 무시)
script_gen.client = OpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────────────────────
# 에러 노트 유틸
# ──────────────────────────────────────────────────────────────
MAX_NOTE_LEN = 1800

def _tail_trace(tb_text: str, lines: int = 6) -> str:
    parts = tb_text.strip().splitlines()[-lines:]
    return "\n".join(parts)

def _shorten(s: str, n: int = 600) -> str:
    s = s or ""
    return (s[:n] + " …(trunc)") if len(s) > n else s

def _bool_to_str(v: bool) -> str:
    return "OK" if v else "X"

def build_error_note(stage: str, e: Exception, ctx: dict) -> str:
    from pathlib import Path as _P
    tb = _tail_trace(traceback.format_exc(), lines=8)
    ffp = ctx.get("ffprobe_path", "")
    ffprobe_ok = bool(ffp and _P(ffp).is_file()) or (shutil.which("ffprobe") is not None)

    tikwm_status = ctx.get("tikwm_status")
    tikwm_keys   = ctx.get("tikwm_keys")
    tikwm_err    = _shorten(ctx.get("tikwm_err",""))

    ytdlp_url = ctx.get("link","")
    host_hint = ""
    try:
        host_hint = ytdlp_url.split("/")[2]
    except Exception:
        pass

    info_lines = [
        f"[단계] {stage}",
        f"[에러] {type(e).__name__}: {str(e)}",
        f"[ffprobe] {_bool_to_str(ffprobe_ok)}",
        f"[ffprobe path] {ffp or '(not set)'}",
        f"[yt-dlp] OK (host: {host_hint or 'unknown'})",
        f"[링크] {_shorten(ctx.get('link',''))}",
        f"[파일] {_shorten(str(ctx.get('out_path','')))}",
        f"[키워드] {_shorten(ctx.get('keyword',''))}",
    ]
    if tikwm_status is not None or tikwm_keys or tikwm_err:
        info_lines.append(f"[TikWM] status={tikwm_status} keys={tikwm_keys or '–'} err={tikwm_err or '–'}")
    if ctx.get("ffprobe_cmd"):
        info_lines.append(f"[ffprobe cmd] {_shorten(' '.join(ctx['ffprobe_cmd']))}")

    info_lines.append("\n[Trace tail]\n" + tb)
    note = "\n".join(info_lines).strip()
    if len(note) > MAX_NOTE_LEN:
        note = note[:MAX_NOTE_LEN] + "\n…(truncated)"
    return note

# ──────────────────────────────────────────────────────────────
# 일반 유틸
# ──────────────────────────────────────────────────────────────
def sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[\r\n]+', ' ', name)
    name = re.sub(r'[<>:\"/\\|?*]', '_', name)
    return name.strip()[:max_len] or "video"

def backoff_sleep(attempt: int, base: float = 1.6, cap: float = 8.0):
    time.sleep(min(cap, base ** max(0, attempt - 1)) + random.random())

# ──────────────────────────────────────────────────────────────
# ffprobe 탐색/사용
# ──────────────────────────────────────────────────────────────
def find_ffprobe() -> str:
    env_path = os.getenv("FFPROBE_PATH")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path))
    here = Path(__file__).resolve().parent
    local = here / "data" / "ffprobe.exe"
    if local.is_file():
        return str(local)
    which = shutil.which("ffprobe")
    return which or ""

def ffprobe_duration(path: Path, ffprobe_path: Optional[str] = None) -> float:
    ffprobe = ffprobe_path or find_ffprobe()
    if not ffprobe:
        raise FileNotFoundError(
            "ffprobe 실행 파일을 찾을 수 없습니다. "
            "FFPROBE_PATH 환경변수에 경로를 지정하거나 ./data/ffprobe.exe 가 있는지 확인하세요."
        )
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    return float(info["format"]["duration"])

# ──────────────────────────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────────────────────────
def tikwm_download(video_url: str, out_path: Path) -> dict:
    api = "https://www.tikwm.com/api/"
    resp = requests.get(api, params={"url": video_url, "hd": 1}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    hdplay = data.get("data", {}).get("hdplay")
    if not hdplay:
        raise RuntimeError("TikTok API 응답에 hdplay URL이 없습니다.")
    with requests.get(hdplay, stream=True, timeout=30) as r, open(out_path, "wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)
    return {"status": resp.status_code, "keys": list(data.get("data", {}).keys())[:10]}

def ytdlp_download(url: str, out_path: Path) -> None:
    ydl_opts = {"outtmpl": str(out_path), "format": "best", "noplaylist": True, "quiet": True}
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# ──────────────────────────────────────────────────────────────
# 시트 접근
# ──────────────────────────────────────────────────────────────
def open_sheet():
    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    gs = gspread.authorize(creds)
    sh = gs.open_by_url(SPREADSHEET_LINK)
    ws = sh.worksheet(SHEET_NAME)
    return ws

def col_index_map(ws) -> Dict[str, int]:
    header = ws.row_values(HEADER_ROW)
    def idx(name: str) -> int: return header.index(name) + 1
    mapping = {
        "작업 선택": idx("작업 선택"),
        "링크": idx("링크"),
        "개별스크립트설정": idx("개별스크립트설정"),
        "스크립트": idx("스크립트"),
        "영상길이": idx("영상길이"),
        "인스타글내용": idx("인스타글내용"),
        "info_keyword": idx("info_keyword"),
        "작업 비고": idx("작업 비고"),
    }
    if "작업파일명" in header:
        mapping["작업파일명"] = idx("작업파일명")
    if "다운로드파일명" in header:
        mapping["다운로드파일명"] = idx("다운로드파일명")
    if "키워드" in header:
        mapping["키워드"] = idx("키워드")
    # ✅ 추가: 쿠팡파트너스링크가 있으면 인덱싱
    if "쿠팡파트너스링크" in header:
        mapping["쿠팡파트너스링크"] = idx("쿠팡파트너스링크")
    return mapping

# ──────────────────────────────────────────────────────────────
# SCRIPT_GEN 파이프라인
# ──────────────────────────────────────────────────────────────
def generate_script_and_assets(video_path: Path, product_info: str,
                               prefer_info_keyword: Optional[str],
                               ffprobe_path: Optional[str]) -> Dict[str, Any]:
    scenes = script_gen.merge_short_scenes(script_gen.detect_scenes(str(video_path)))
    scene_texts = []
    for (s, e, frame) in scenes:
        desc = script_gen.describe_scene(frame, product_info or "")
        scene_texts.append(((s, e), desc))

    total_sec = ffprobe_duration(video_path, ffprobe_path)
    overall   = script_gen.describe_overall_video(scene_texts, total_sec, product_info or "")
    audience  = script_gen.generate_target_audience(overall)

    if prefer_info_keyword and prefer_info_keyword.strip():
        info_kw = prefer_info_keyword.strip()
    else:
        coupang_list = script_gen.generate_coupang_keywords(product_info or "")
        best_kw      = script_gen.generate_best_coupang_keyword(coupang_list)
        info_kw      = script_gen.extract_info_keyword(best_kw)

    draft        = script_gen.build_final_script(scene_texts, total_sec, overall, audience, product_info or "")
    max_chars    = int(round(total_sec * 9))
    final_script = script_gen.fit_script_length(draft, max_chars, total_sec, audience, info_kw)
    insta        = script_gen.generate_instagram_content(final_script, info_kw)

    return {
        "script": final_script,
        "overall": overall,
        "audience": audience,
        "info_keyword": info_kw,
        "insta": insta,
        "duration": total_sec,
    }

# ──────────────────────────────────────────────────────────────
# 메인 처리
# ──────────────────────────────────────────────────────────────
def process():
    ws = open_sheet()
    idx = col_index_map(ws)

    front_ment = ws.acell("B5").value or ""
    back_ment  = ws.acell("B6").value or ""

    values = ws.get_all_values()
    rows = values[HEADER_ROW:]

    videos_dir = Path("videos")
    videos_dir.mkdir(exist_ok=True)

    ffprobe_path = find_ffprobe()

    for i, row in enumerate(rows):
        sheet_row = HEADER_ROW + i + 1
        stage = "INIT"
        ctx: Dict[str, Any] = {}

        try:
            stage = "READ_ROW"
            sel = row[idx["작업 선택"] - 1].strip() if len(row) >= idx["작업 선택"] else ""
            if sel != "영상다운로드":
                continue

            link = row[idx["링크"] - 1].strip() if len(row) >= idx["링크"] else ""
            if not link:
                raise RuntimeError("링크 값이 비어 있습니다.")

            keyword_val = (row[idx["키워드"] - 1].strip()
                           if "키워드" in idx and len(row) >= idx["키워드"] else "")
            tail = link.rstrip("/").split("/")[-1] if link else ""
            base_hint = sanitize_filename(keyword_val or tail or "video")

            ts = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{base_hint}_{ts}.mp4"
            out_path = videos_dir / filename

            ctx.update({
                "link": link, "keyword": keyword_val,
                "out_path": str(out_path), "ffprobe_path": ffprobe_path
            })

            # 다운로드
            if "instagram.com" in link:
                stage = "DOWNLOAD_INSTAGRAM_YTDLP"
                ytdlp_download(link, out_path)
            else:
                stage = "DOWNLOAD_TIKTOK"
                twm_meta = tikwm_download(link, out_path)
                if isinstance(twm_meta, dict):
                    ctx["tikwm_status"] = twm_meta.get("status")
                    ctx["tikwm_keys"]   = twm_meta.get("keys")

            time.sleep(0.2)

            # 길이(ffprobe) — 분기 전에 항상 계산
            stage = "FFPROBE_DURATION"
            ctx["ffprobe_cmd"] = [ffprobe_path or "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out_path)]
            duration = ffprobe_duration(out_path, ffprobe_path)

            stage = "SCRIPT_PREPARE"
            # 기존: info_kw_existing = row[...] 로 읽던 부분 삭제/대체
            info_kw_existing = (ws.cell(sheet_row, idx["info_keyword"]).value or "") if "info_keyword" in idx else ""
            indiv_script = row[idx["개별스크립트설정"] - 1].strip() if len(row) >= idx["개별스크립트설정"] else ""

            if indiv_script:
                stage = "SCRIPT_USE_INDIVIDUAL"
                final_script_body = indiv_script
                info_kw_to_use = info_kw_existing or ""
                if not info_kw_to_use:
                    stage = "INFO_KEYWORD_FALLBACK"
                    product_info = keyword_val or base_hint
                    coupang_list = script_gen.generate_coupang_keywords(product_info or "")
                    best_kw = script_gen.generate_best_coupang_keyword(coupang_list)
                    info_kw_to_use = script_gen.extract_info_keyword(best_kw)
                stage = "INSTA_FROM_INDIVIDUAL"
                insta_text = script_gen.generate_instagram_content(final_script_body, info_kw_to_use)
                generated_info_kw = info_kw_to_use if not info_kw_existing else None

                import re as _re
                effective_info_kw = info_kw_existing or info_kw_to_use
                final_script_body = _re.sub(r"\{\s*info_keyword\s*\}", effective_info_kw, final_script_body)

            else:
                stage = "SCRIPT_GEN_PIPELINE"
                product_info = keyword_val or base_hint
                pack = generate_script_and_assets(out_path, product_info, info_kw_existing or None, ffprobe_path)
                final_script_body = pack["script"]
                # duration = pack.get("duration", duration)  # 필요 시 덮어쓰기
                insta_text = pack["insta"]
                generated_info_kw = None if info_kw_existing else pack["info_keyword"]

                import re as _re
                effective_info_kw = info_kw_existing or pack["info_keyword"]
                final_script_body = _re.sub(r"\{\s*info_keyword\s*\}", effective_info_kw, final_script_body)

            # B5/B6 삽입
            stage = "MENT_INSERT"
            parts = []
            if front_ment: parts.append(front_ment)
            parts.append(final_script_body)
            if back_ment: parts.append(back_ment)
            final_script = "\n".join(parts)


            # --------------------------
            # ✅ 쿠팡 파트너스 링크 생성
            # --------------------------
            partner_link = ""
            partner_note = ""
            try:
                # 링크 생성용 키워드: "키워드"가 최우선, 없으면 info_keyword로 대체
                kw_for_link = (keyword_val or effective_info_kw or "").strip()
                if kw_for_link:
                    search_url = (
                        "https://www.coupang.com/np/search"
                        "?component=&q=" + requests.utils.quote(kw_for_link, safe='') +
                        "&channel=user"
                    )
                    # script_gen의 함수를 재사용 (SUB_ID도 내부에서 사용)
                    result = script_gen.convert_to_affiliate_link(search_url, getattr(script_gen, "SUB_ID", ""))
                    data = result.get("data") or []
                    if data and isinstance(data, list):
                        d0 = data[0] or {}
                        partner_link = d0.get("shortenUrl") or d0.get("landingUrl") or ""
                    # 딥링크가 비면 products/search로 우회
                    if not partner_link:
                        partner_link = script_gen.affiliate_search_fallback(kw_for_link, getattr(script_gen, "SUB_ID", "")) or ""
                        if not partner_link:
                            partner_note = f"[Coupang] deeplink empty → products/search도 빈값: {result}"
                else:
                    partner_note = "[Coupang] keyword/info_keyword 둘 다 비어 링크 스킵"
            except Exception as e:
                partner_link = ""
                partner_note = f"[Coupang] error: {type(e).__name__}: {e}"









            # 업데이트 준비
            stage = "SHEET_BATCH_UPDATE_PREP"
            batch = []

            batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["스크립트"]), "values": [[final_script]]})
            batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["영상길이"]), "values": [[round(float(duration), 2)]]})
            batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["인스타글내용"]), "values": [[insta_text]]})
            if generated_info_kw:
                batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["info_keyword"]), "values": [[generated_info_kw]]})
            if "작업파일명" in idx:
                batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업파일명"]), "values": [[filename]]})
            if "다운로드파일명" in idx:
                batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["다운로드파일명"]), "values": [[filename]]})
            # batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 선택"]), "values": [["작업 완료"]]})


            if "쿠팡파트너스링크" in idx:
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(sheet_row, idx["쿠팡파트너스링크"]),
                    "values": [[partner_link]]
                })
            if partner_note:
                # 이미 다른 비고가 있다면 덧붙이기보다는 덮어써도 OK. 필요 시 합치기로 바꾸세요.
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 비고"]),
                    "values": [[partner_note]]
                })



            # ★ 추가: 성공 시 상태 전환 — '작업 선택' → '스크립트생성'
            batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 선택"]), "values": [["TTS생성"]]})


            # 배치 업데이트(429 백오프)
            stage = "SHEET_BATCH_UPDATE"
            for attempt in range(1, 6):
                try:
                    ws.batch_update(batch)
                    break
                except gspread.exceptions.APIError as e:
                    if "429" in str(e) and attempt < 5:
                        backoff_sleep(attempt); continue
                    raise

            # 최종 치환 보정: 시트 info_keyword 현재값으로 {info_keyword} → 실제값
            try:
                import re as _re
                info_kw_now = ws.cell(sheet_row, idx["info_keyword"]).value or ""
                if info_kw_now:
                    substituted = _re.sub(r"\{\s*info_keyword\s*\}", info_kw_now, final_script)
                    if substituted != final_script:
                        ws.update_cell(sheet_row, idx["스크립트"], substituted)
            except Exception as _post_e:
                try:
                    note = build_error_note("POST_SUBSTITUTE_INFO_KEYWORD", _post_e, {
                        "link": ctx.get("link",""),
                        "out_path": ctx.get("out_path",""),
                        "keyword": ctx.get("keyword",""),
                        "ffprobe_path": ctx.get("ffprobe_path",""),
                    })
                    ws.update_cell(sheet_row, idx["작업 비고"], note[:MAX_NOTE_LEN])
                except Exception:
                    pass

        except Exception as e:
            if stage.startswith("DOWNLOAD_TIKTOK"):
                ctx.setdefault("tikwm_err", "다운로드 단계에서 예외 발생")
            note = build_error_note(stage, e, ctx)
            batch_err = [
                {"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 선택"]), "values": [["작업 중 에러"]]},
                {"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 비고"]), "values": [[note]]},
            ]
            try:
                ws.batch_update(batch_err)
            except Exception:
                try:
                    ws.update_cell(sheet_row, idx["작업 선택"], "작업 중 에러")
                    ws.update_cell(sheet_row, idx["작업 비고"], note[:MAX_NOTE_LEN])
                except Exception:
                    pass

# 스크립트 단독 실행도 가능하게
if __name__ == "__main__":
    process()
