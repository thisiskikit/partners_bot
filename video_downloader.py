# video_downloader.py
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import random
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

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

def log(msg: str, level: str = "INFO"):
    """간단 로그 출력"""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {level} | {msg}")

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
    ytdlp_auth   = _shorten(ctx.get("ytdlp_auth",""))
    ytdlp_try    = _shorten(ctx.get("ytdlp_attempts",""))
    video_codec  = _shorten(ctx.get("video_codec",""))
    video_tag    = _shorten(ctx.get("video_codec_tag",""))

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
    if ytdlp_auth:
        info_lines.append(f"[yt-dlp auth] {ytdlp_auth}")
    if ytdlp_try:
        info_lines.append(f"[yt-dlp attempts] {ytdlp_try}")
    if video_codec or video_tag:
        info_lines.append(f"[video codec] name={video_codec or '–'} tag={video_tag or '–'}")
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

def _env_text(name: str) -> str:
    return (os.getenv(name) or "").strip()

def _first_existing_file_from_env(*names: str) -> str:
    for key in names:
        raw = _env_text(key)
        if not raw:
            continue
        p = Path(raw).expanduser()
        if p.is_file():
            return str(p)
    return ""

def _parse_browser_cookie_spec(spec: str) -> Optional[Tuple[str, Optional[str], Optional[str], Optional[str]]]:
    """
    지원 형식:
    - chrome
    - chrome:Default
    - chrome+basictext:Default
    - firefox:default-release::container_name
    """
    raw = (spec or "").strip()
    if not raw:
        return None

    container = None
    left = raw
    if "::" in raw:
        left, container = raw.split("::", 1)

    profile = None
    if ":" in left:
        left, profile = left.split(":", 1)

    browser = left
    keyring = None
    if "+" in left:
        browser, keyring = left.split("+", 1)

    browser = (browser or "").strip().lower()
    if not browser:
        return None

    return (
        browser,
        (profile or "").strip() or None,
        (keyring or "").strip() or None,
        (container or "").strip() or None,
    )

def _base_ydl_opts(out_path: Path) -> Dict[str, Any]:
    return {
        "outtmpl": str(out_path),
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 2,
        "sleep_interval_requests": 1.0,
        "max_sleep_interval_requests": 2.0,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        },
    }

def _instagram_ydl_attempts(out_path: Path) -> List[Tuple[str, Dict[str, Any]]]:
    base = _base_ydl_opts(out_path)
    attempts: List[Tuple[str, Dict[str, Any]]] = [("no-auth", dict(base))]

    cookie_file = _first_existing_file_from_env("INSTAGRAM_COOKIES_FILE", "YTDLP_COOKIES_FILE")
    if cookie_file:
        opts = dict(base)
        opts["cookiefile"] = cookie_file
        attempts.append(("cookiefile", opts))

    specs: List[Tuple[str, Optional[str], Optional[str], Optional[str]]] = []
    raw_specs = _env_text("YTDLP_COOKIES_FROM_BROWSER")
    auto_browser = _env_text("YTDLP_AUTO_BROWSER_COOKIES").lower() in ("1", "true", "yes", "on")
    if raw_specs:
        for token in raw_specs.split(","):
            parsed = _parse_browser_cookie_spec(token)
            if parsed:
                specs.append(parsed)
    elif auto_browser:
        profile = _env_text("YTDLP_BROWSER_PROFILE") or None
        for browser in ("chrome", "edge", "firefox"):
            specs.append((browser, profile, None, None))

    seen = set()
    for spec in specs:
        dedup_key = (spec[0], spec[1] or "", spec[2] or "", spec[3] or "")
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        opts = dict(base)
        opts["cookiesfrombrowser"] = spec
        label = f"browser:{spec[0]}" + (f":{spec[1]}" if spec[1] else "")
        attempts.append((label, opts))

    return attempts

def _normalize_escaped_url(raw: str) -> str:
    s = raw or ""
    for _ in range(8):
        s = s.replace("\\/", "/")
    try:
        s = s.encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    for _ in range(4):
        s = s.replace("\\/", "/")
    return s

def _extract_instagram_embed_video_url(url: str) -> str:
    m = re.search(r"instagram\.com/(reel|p|tv)/([^/?#]+)", url or "", re.IGNORECASE)
    if not m:
        raise RuntimeError("Instagram URL에서 shortcode를 찾지 못했습니다.")

    media_type = m.group(1).lower()
    shortcode = m.group(2)
    embed_url = f"https://www.instagram.com/{media_type}/{shortcode}/embed/captioned/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(embed_url, timeout=20, headers=headers)
    resp.raise_for_status()

    html_text = resp.text or ""
    m_video = re.search(r'\\\"video_url\\\":\\\"([^\\\"]+)\\\"', html_text)
    if not m_video:
        raise RuntimeError("embed 페이지에서 video_url을 찾지 못했습니다.")

    video_url = _normalize_escaped_url(m_video.group(1))
    if not video_url.lower().startswith("http"):
        raise RuntimeError("추출된 video_url 형식이 올바르지 않습니다.")
    return video_url

def _instagram_embed_fallback_download(url: str, out_path: Path) -> None:
    video_url = _extract_instagram_embed_video_url(url)
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.instagram.com/"}
    with requests.get(video_url, stream=True, timeout=40, headers=headers) as r, open(out_path, "wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
    if not out_path.exists() or out_path.stat().st_size <= 0:
        raise RuntimeError("embed fallback 다운로드 결과 파일이 비어 있습니다.")

# ──────────────────────────────────────────────────────────────
# ffprobe / ffmpeg 탐색/사용
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

def ffprobe_video_codec(path: Path, ffprobe_path: Optional[str] = None) -> Tuple[str, str]:
    ffprobe = ffprobe_path or find_ffprobe()
    if not ffprobe:
        return "", ""
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,codec_tag_string",
        "-of", "json",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout or "{}")
    streams = info.get("streams") or []
    if not streams:
        return "", ""
    s0 = streams[0] or {}
    codec_name = str(s0.get("codec_name") or "").strip().lower()
    codec_tag = str(s0.get("codec_tag_string") or "").strip().lower()
    return codec_name, codec_tag

# 🔽 ffmpeg 탐색
def find_ffmpeg() -> str:
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path))
    here = Path(__file__).resolve().parent
    local = here / "data" / "ffmpeg.exe"
    if local.is_file():
        return str(local)
    which = shutil.which("ffmpeg")
    return which or ""

def file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return path.stat().st_size / (1024 * 1024)

def shrink_video_if_too_big(
    input_path: Path,
    ffprobe_path: Optional[str],
    target_mb: float = 60.0,
    max_height: int = 1080,
) -> Path:
    """
    input_path 용량이 target_mb를 넘으면 ffmpeg로 재인코딩해서 용량 줄이고,
    더 작은 파일이 만들어지면 그걸 반환합니다.
    """
    size_mb = file_size_mb(input_path)
    if size_mb <= 0 or size_mb <= target_mb:
        return input_path  # 이미 충분히 작음

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        log(f"ffmpeg 미발견 → 용량 {size_mb:.1f}MB 그대로 사용", "WARNING")
        return input_path

    try:
        # 먼저 길이 얻기
        try:
            dur = ffprobe_duration(input_path, ffprobe_path)
        except Exception:
            dur = None

        # 대략적인 타겟 비트레이트 계산 (오디오 128kbps 가정)
        if dur and dur > 0:
            total_bits = target_mb * 1024 * 1024 * 8
            target_bitrate = int(total_bits / dur)  # bps
        else:
            target_bitrate = 1_000_000  # 대략 1Mbps fallback

        video_bps = max(target_bitrate - 128_000, 300_000)
        video_k = video_bps // 1000

        tmp_out = input_path.with_suffix(".small.mp4")
        log(
            f"ffmpeg 재인코딩 시작: {input_path.name} ({size_mb:.1f}MB → <= {target_mb}MB 목표, "
            f"video≈{video_k}k, max_height={max_height})",
            "INFO",
        )

        cmd = [
            ffmpeg,
            "-y",
            "-i", str(input_path),
            "-vf", f"scale=-2:{max_height}",
            "-c:v", "libx264",
            "-b:v", f"{video_k}k",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "128k",
            str(tmp_out),
        ]
        subprocess.run(cmd, check=True)

        new_size = file_size_mb(tmp_out)
        if new_size > 0 and new_size < size_mb:
            # 교체
            input_path.unlink(missing_ok=True)
            log(f"영상 압축 완료: {size_mb:.1f}MB → {new_size:.1f}MB ({tmp_out.name})", "INFO")
            return tmp_out
        else:
            log(
                f"압축 결과가 충분히 작지 않음({new_size:.1f}MB) → 원본 유지",
                "WARNING",
            )
            tmp_out.unlink(missing_ok=True)
            return input_path
    except Exception as e:
        log(f"영상 압축 실패: {type(e).__name__}: {e}", "ERROR")
        return input_path

# ──────────────────────────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────────────────────────
def _stream_download(url: str, out_path: Path, *, timeout: int = 40, referer: str = "") -> None:
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer:
        headers["Referer"] = referer
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as r, open(out_path, "wb") as f:
        r.raise_for_status()
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)
    if not out_path.exists() or out_path.stat().st_size <= 0:
        raise RuntimeError("다운로드 결과 파일이 비어 있습니다.")

def _pick_tikwm_play_url(payload: Dict[str, Any]) -> Tuple[str, str]:
    # 호환성 이슈(bvc2) 회피를 위해 일반 play를 우선 사용
    for key in ("play", "wmplay", "playwm", "hdplay"):
        v = payload.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return key, v
    raise RuntimeError(f"TikWM 응답에 재생 URL이 없습니다. keys={list(payload.keys())[:12]}")

def tikwm_download(video_url: str, out_path: Path) -> dict:
    apis = ["https://www.tikwm.com/api/", "https://tikwm.com/api/"]
    # hd=1이 bvc2를 주는 경우가 있어 기본은 hd=0 먼저 시도
    hds = [0, 1]
    errors: List[str] = []
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.tikwm.com/",
    }

    for api in apis:
        for hd in hds:
            try:
                resp = requests.get(api, params={"url": video_url, "hd": hd}, timeout=20, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                payload = data.get("data") or {}
                code = data.get("code")
                if code not in (0, "0", None):
                    msg = data.get("msg") or data.get("message") or ""
                    raise RuntimeError(f"code={code} msg={msg}".strip())
                src_key, play_url = _pick_tikwm_play_url(payload)
                _stream_download(play_url, out_path, timeout=45, referer="https://www.tikwm.com/")
                log(f"TikWM 다운로드 성공(api={api}, hd={hd}, key={src_key})", "INFO")
                return {
                    "status": resp.status_code,
                    "keys": list(payload.keys())[:12],
                    "api": api,
                    "hd": hd,
                    "source": src_key,
                }
            except Exception as e:
                errors.append(f"{api}[hd={hd}] {type(e).__name__}: {e}")
                try:
                    if out_path.exists() and out_path.stat().st_size == 0:
                        out_path.unlink(missing_ok=True)
                except Exception:
                    pass

    detail = " | ".join(_shorten(x, 220) for x in errors[-6:])
    raise RuntimeError(f"TikWM 다운로드 실패: {detail}")

def ytdlp_download(url: str, out_path: Path) -> Dict[str, str]:
    lower_url = (url or "").lower()
    is_instagram = "instagram.com" in lower_url

    if is_instagram:
        attempts = _instagram_ydl_attempts(out_path)
    else:
        attempts = [("default", _base_ydl_opts(out_path))]

    tried_labels: List[str] = []
    errors: List[str] = []
    last_exc: Optional[Exception] = None

    for label, ydl_opts in attempts:
        tried_labels.append(label)
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            log(f"yt-dlp 다운로드 성공({label})", "INFO")
            return {"auth": label, "attempts": ", ".join(tried_labels)}
        except Exception as e:
            last_exc = e
            errors.append(f"{label}: {type(e).__name__}: {e}")
            log(f"yt-dlp 다운로드 실패({label}): {type(e).__name__}: {e}", "WARNING")
            try:
                if out_path.exists() and out_path.stat().st_size == 0:
                    out_path.unlink(missing_ok=True)
            except Exception:
                pass
            if not is_instagram:
                break

    if is_instagram:
        hint = (
            "Instagram 다운로드 실패. 로그인/쿠키 인증이 필요할 수 있습니다. "
            ".env에 INSTAGRAM_COOKIES_FILE(쿠키 txt) 또는 "
            "YTDLP_COOKIES_FROM_BROWSER=chrome[:프로필명] 을 설정해 주세요. "
            "(자동 브라우저 쿠키 시도는 YTDLP_AUTO_BROWSER_COOKIES=1 일 때만 동작)"
        )
        try:
            _instagram_embed_fallback_download(url, out_path)
            log("Instagram embed fallback 다운로드 성공(embed-fallback)", "INFO")
            return {"auth": "embed-fallback", "attempts": ", ".join(tried_labels + ["embed-fallback"])}
        except Exception as embed_e:
            errors.append(f"embed-fallback: {type(embed_e).__name__}: {embed_e}")
    else:
        hint = "yt-dlp 다운로드 실패"

    detail = " | ".join(_shorten(x, 240) for x in errors[-4:])
    if detail:
        hint = f"{hint} (시도: {detail})"
    raise RuntimeError(hint) from last_exc

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
def process(target_rows: Optional[List[int]] = None) -> List[int]:
    ws = open_sheet()
    idx = col_index_map(ws)

    front_ment = ws.acell("B5").value or ""
    back_ment  = ws.acell("B6").value or ""

    values = ws.get_all_values()
    rows = values[HEADER_ROW:]

    videos_dir = Path("videos")
    videos_dir.mkdir(exist_ok=True)

    ffprobe_path = find_ffprobe()
    target_set = set(target_rows or [])
    processed_rows: List[int] = []

    for i, row in enumerate(rows):
        sheet_row = HEADER_ROW + i + 1
        if target_set and sheet_row not in target_set:
            continue
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
            if "instagram.com" in link.lower():
                stage = "DOWNLOAD_INSTAGRAM_YTDLP"
                ytdlp_meta = ytdlp_download(link, out_path)
                if isinstance(ytdlp_meta, dict):
                    ctx["ytdlp_auth"] = ytdlp_meta.get("auth", "")
                    ctx["ytdlp_attempts"] = ytdlp_meta.get("attempts", "")
            else:
                stage = "DOWNLOAD_TIKTOK"
                try:
                    twm_meta = tikwm_download(link, out_path)
                    if isinstance(twm_meta, dict):
                        ctx["tikwm_status"] = twm_meta.get("status")
                        ctx["tikwm_keys"]   = twm_meta.get("keys")
                except Exception as twm_e:
                    ctx["tikwm_err"] = f"{type(twm_e).__name__}: {twm_e}"
                    stage = "DOWNLOAD_TIKTOK_YTDLP_FALLBACK"
                    ytdlp_meta = ytdlp_download(link, out_path)
                    if isinstance(ytdlp_meta, dict):
                        ctx["ytdlp_auth"] = ytdlp_meta.get("auth", "")
                        ctx["ytdlp_attempts"] = ytdlp_meta.get("attempts", "")
                    log("TikTok 다운로드: TikWM 실패 -> yt-dlp fallback 성공", "INFO")

            time.sleep(0.2)

            # TikWM이 bvc2/unknown 코덱을 줄 때 오디오 교체 단계가 실패하므로 즉시 yt-dlp로 교체 시도
            if ffprobe_path:
                stage = "CHECK_VIDEO_CODEC"
                codec_name, codec_tag = ffprobe_video_codec(out_path, ffprobe_path)
                ctx["video_codec"] = codec_name
                ctx["video_codec_tag"] = codec_tag
                incompatible_codec = (codec_name in ("", "none", "unknown")) or (codec_tag == "bvc2")
                if incompatible_codec and "instagram.com" not in link.lower():
                    log(
                        f"코덱 호환성 경고(name={codec_name or '-'}, tag={codec_tag or '-'}) -> yt-dlp 재시도",
                        "WARNING",
                    )
                    out_path.unlink(missing_ok=True)
                    stage = "DOWNLOAD_TIKTOK_YTDLP_CODEC_FALLBACK"
                    ytdlp_meta = ytdlp_download(link, out_path)
                    if isinstance(ytdlp_meta, dict):
                        ctx["ytdlp_auth"] = ytdlp_meta.get("auth", "")
                        ctx["ytdlp_attempts"] = ytdlp_meta.get("attempts", "")
                    codec_name, codec_tag = ffprobe_video_codec(out_path, ffprobe_path)
                    ctx["video_codec"] = codec_name
                    ctx["video_codec_tag"] = codec_tag
                    still_incompatible = (codec_name in ("", "none", "unknown")) or (codec_tag == "bvc2")
                    if still_incompatible:
                        raise RuntimeError(
                            f"다운로드 영상 코덱 호환 불가(codec={codec_name or '-'}, tag={codec_tag or '-'})"
                        )

            # 🔽 용량 체크 + 필요 시 재인코딩 (20MB 초과 시)
            stage = "SHRINK_IF_NEEDED"
            out_path = shrink_video_if_too_big(out_path, ffprobe_path, target_mb=45.0, max_height=720)
            ctx["out_path"] = str(out_path)

            # 길이(ffprobe) — (압축 후 기준으로) 계산
            stage = "FFPROBE_DURATION"
            ctx["ffprobe_cmd"] = [ffprobe_path or "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out_path)]
            duration = ffprobe_duration(out_path, ffprobe_path)

            stage = "SCRIPT_PREPARE"
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
                kw_for_link = (keyword_val or effective_info_kw or "").strip()
                if kw_for_link:
                    search_url = (
                        "https://www.coupang.com/np/search"
                        "?component=&q=" + requests.utils.quote(kw_for_link, safe='') +
                        "&channel=user"
                    )
                    result = script_gen.convert_to_affiliate_link(search_url, getattr(script_gen, "SUB_ID", ""))
                    data = result.get("data") or []
                    if data and isinstance(data, list):
                        d0 = data[0] or {}
                        partner_link = d0.get("shortenUrl") or d0.get("landingUrl") or ""
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

            if "쿠팡파트너스링크" in idx:
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(sheet_row, idx["쿠팡파트너스링크"]),
                    "values": [[partner_link]]
                })
            if partner_note:
                batch.append({
                    "range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 비고"]),
                    "values": [[partner_note]]
                })

            # 상태 전환: '작업 선택' → 'TTS생성'
            batch.append({"range": gspread.utils.rowcol_to_a1(sheet_row, idx["작업 선택"]), "values": [["TTS생성"]]})

            stage = "SHEET_BATCH_UPDATE"
            for attempt in range(1, 6):
                try:
                    ws.batch_update(batch)
                    break
                except gspread.exceptions.APIError as e:
                    if "429" in str(e) and attempt < 5:
                        backoff_sleep(attempt); continue
                    raise

            # 최종 치환 보정
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
            continue

        processed_rows.append(sheet_row)

    return processed_rows

# 스크립트 단독 실행도 가능하게
if __name__ == "__main__":
    process()
