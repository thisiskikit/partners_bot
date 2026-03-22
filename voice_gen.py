#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tts_ge.py (생성하기 시트 전용)

요구사항 반영
- 대상 스프레드시트:
  https://docs.google.com/spreadsheets/d/1EknnoEQ3HSfUSKeJsPnRZID-lw0Diy-OVwgiQCfTeb8/edit?usp=sharing
- 시트: '생성하기'
- 헤더: 4행
- 처리 대상: '작업 선택' == '작업 시작' 인 행만 처리

동작
1) '개별스크립트설정' 텍스트 → ElevenLabs TTS 생성
2) '영상길이' 값만큼 오디오 stretch (기본: pyrubberband, 실패 시 ffmpeg atempo fallback)
3) stretch 된 오디오를 mp4(검정 배경 영상 + 오디오)로 변환
4) '작업 비고'에 작업 결과 기록
5) 이메일 발송 (B11~B14: TO/CC/BCC/REPLY-TO)
   - 제목: '기존작업일자' + '음성작업일자' + '개별스크립트설정' 첫 줄
   - 내용: '개별스크립트설정' 전체 + 작업 비고 + 생성 파일 경로 등
   - mp4 파일 첨부

상태 처리
- 성공 시: '작업 선택' → NEXT_STATUS_AFTER_SUCCESS (기본: 작업 완료)
- 오류 시: '작업 선택' → '작업 중 에러', '작업 비고'에 상세 기록

추가 반영 (요청사항)
- '생성하기' 시트의 B17~B23 값을 읽어 ElevenLabs 파라미터로 적용
  B17: ELEVENLABS_VOICE_ID  -> voice_id
  B18: ELEVENLABS_MODEL_ID  -> model_id
  B19: ELEVENLABS_STABILITY -> voice_settings.stability
  B20: ELEVENLABS_SIMILARITY-> voice_settings.similarity_boost
  B21: ELEVENLABS_STYLE     -> voice_settings.style
  B22: ELEVENLABS_SPEED     -> voice_settings.speed
  B23: ELEVENLABS_SPK_BOOST -> voice_settings.use_speaker_boost (bool)
"""

from __future__ import annotations

import os
import re
import json
import time
import shutil
import random
import traceback
import subprocess
import smtplib
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, Any, List

import numpy as np
import librosa
import soundfile as sf
import pyrubberband as pyrb

import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

from elevenlabs.client import ElevenLabs
# VoiceSettings는 SDK 버전에 따라 없거나 시그니처가 다를 수 있어 안전하게 처리
try:
    from elevenlabs import VoiceSettings  # type: ignore
except Exception:
    VoiceSettings = None  # type: ignore

from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from dotenv import load_dotenv


# =============================================================================
# .env 로드
# =============================================================================
DOTENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)


# =============================================================================
# 기본 설정
# =============================================================================
SPREADSHEET_LINK_DEFAULT = "https://docs.google.com/spreadsheets/d/1EknnoEQ3HSfUSKeJsPnRZID-lw0Diy-OVwgiQCfTeb8/edit?usp=sharing"
SPREADSHEET_LINK = (os.getenv("SPREADSHEET_LINK_voice") or SPREADSHEET_LINK_DEFAULT).strip()

SHEET_NAME = "생성하기"
HEADER_ROW = 4

NEXT_STATUS_AFTER_SUCCESS = (os.getenv("NEXT_STATUS_AFTER_SUCCESS") or "작업 완료").strip()

# 출력 폴더
SCRIPT_DIR = Path(__file__).resolve().parent
DONE_ROOT = SCRIPT_DIR / "done"
AUDIO_DIR = SCRIPT_DIR / "audios"
MP4_DIR   = SCRIPT_DIR / "mp4"
TMP_DIR   = SCRIPT_DIR / "tmp"

for d in (DONE_ROOT, AUDIO_DIR, MP4_DIR, TMP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# 비디오 생성 기본 파라미터
VIDEO_SIZE = (os.getenv("VIDEO_SIZE") or "1080x1920").strip()  # widthxheight
VIDEO_FPS  = int((os.getenv("VIDEO_FPS") or "30").strip())

MAX_NOTE_LEN = 1800


# =============================================================================
# rubberband PATH 보강 (pyrubberband가 rubberband.exe를 호출할 수 있게)
# =============================================================================
DATA_DIR = SCRIPT_DIR / "data"
RB_DIR   = DATA_DIR / "rubberband"

os.environ["PATH"] = str(DATA_DIR) + os.pathsep + os.environ.get("PATH", "")
os.environ["PATH"] = str(RB_DIR)   + os.pathsep + os.environ.get("PATH", "")

_rb = shutil.which("rubberband")
if not _rb:
    raise RuntimeError(
        "rubberband 실행파일을 찾지 못했습니다. "
        f"다음 위치에 rubberband.exe를 두세요: {RB_DIR}"
    )


# =============================================================================
# ENV 유틸
# =============================================================================
def _clean(s: Optional[str]) -> str:
    return (s or "").strip().strip('"').strip("'").replace("\u200b", "").replace("\ufeff", "")

def env_path_first(*names: str) -> str:
    for n in names:
        v = _clean(os.getenv(n))
        if v:
            return v
    return ""

CREDS = env_path_first("CREDS_FILE_OHL1", "CREDS_FILE_OHL2", "GOOGLE_APPLICATION_CREDENTIALS")
if not CREDS:
    raise RuntimeError("CREDS_FILE_OHL1(또는 CREDS_FILE_OHL2/GOOGLE_APPLICATION_CREDENTIALS) 를 .env에 설정하세요.")

ELEVEN_API_KEY = _clean(os.getenv("ELEVENLABS_API_KEY"))
if not ELEVEN_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY 를 .env에 설정하세요.")

ELEVEN_VOICE_ID_ENV  = _clean(os.getenv("ELEVENLABS_VOICE_ID"))
ELEVEN_MODEL_ID_ENV  = _clean(os.getenv("ELEVENLABS_MODEL_ID")) or "eleven_multilingual_v2"

# output_format 기본값은 호환성 좋은 mp3로 설정(원하시면 .env로 변경)
ELEVEN_OUTPUT_FORMAT = _clean(os.getenv("ELEVENLABS_OUTPUT_FORMAT")) or "mp3_44100_128"

SMTP_HOST = _clean(os.getenv("SMTP_HOST")) or "smtp.gmail.com"
SMTP_PORT = int(_clean(os.getenv("SMTP_PORT")) or "587")
SMTP_USER = _clean(os.getenv("SMTP_USER"))
SMTP_PASS = _clean(os.getenv("SMTP_PASS"))
SMTP_FROM_NAME = _clean(os.getenv("SMTP_FROM_NAME")) or "KIKIT"

if not (SMTP_USER and SMTP_PASS):
    raise RuntimeError("SMTP_USER / SMTP_PASS 를 .env에 설정하세요. (Gmail은 앱 비밀번호 권장)")


# =============================================================================
# Google Sheets 클라이언트
# =============================================================================
gs_creds = Credentials.from_service_account_file(
    CREDS,
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gc = gspread.authorize(gs_creds)

# ElevenLabs 클라이언트
eleven = ElevenLabs(api_key=ELEVEN_API_KEY)


# =============================================================================
# 공용 유틸
# =============================================================================
def sanitize_name(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[\r\n]+", " ", name or "")
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return (name or "file")[:max_len]

def clamp_note(s: str) -> str:
    s = s or ""
    return s[:MAX_NOTE_LEN] + ("\n…(truncated)" if len(s) > MAX_NOTE_LEN else "")

def _tail(tb: str, n: int = 10) -> str:
    lines = (tb or "").splitlines()
    return "\n".join(lines[-n:])

def find_ffmpeg() -> str:
    env_path = _clean(os.getenv("FFMPEG_PATH"))
    if env_path and Path(env_path).is_file():
        return env_path
    local = SCRIPT_DIR / "data" / "ffmpeg.exe"
    if local.is_file():
        return str(local)
    which = shutil.which("ffmpeg")
    return which or ""

def find_ffprobe() -> str:
    env_path = _clean(os.getenv("FFPROBE_PATH"))
    if env_path and Path(env_path).is_file():
        return env_path
    local = SCRIPT_DIR / "data" / "ffprobe.exe"
    if local.is_file():
        return str(local)
    which = shutil.which("ffprobe")
    return which or ""

def parse_duration_to_sec(v: str) -> float:
    """
    '영상길이' 값 파싱:
    - "12.34" → 12.34
    - "15" → 15
    - "00:15" → 15
    - "01:02:03" → 3723
    - "15s" → 15
    """
    s = _clean(v)
    if not s:
        raise ValueError("영상길이가 비어 있습니다.")

    s2 = s.lower().replace("seconds", "s").replace("sec", "s").strip()

    # hh:mm:ss or mm:ss
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", s2):
        parts = [int(x) for x in s2.split(":")]
        if len(parts) == 2:
            mm, ss = parts
            return float(mm * 60 + ss)
        hh, mm, ss = parts
        return float(hh * 3600 + mm * 60 + ss)

    # 15s
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*s", s2)
    if m:
        return float(m.group(1))

    # plain float/int (comma allowed)
    try:
        return float(s2.replace(",", "."))
    except Exception:
        raise ValueError(f"영상길이 파싱 실패: '{s}'")

def safe_batch_update(ws, batch: List[Dict], max_attempts: int = 6):
    if not batch:
        return
    base = 1.25
    for attempt in range(1, max_attempts + 1):
        try:
            ws.batch_update(batch)
            return
        except APIError as e:
            msg = str(e)
            if any(code in msg for code in ("429", "500", "502", "503", "504")) and attempt < max_attempts:
                sleep_s = min(20.0, (base ** (attempt - 1))) + random.uniform(0, 0.7)
                time.sleep(sleep_s)
                continue
            raise

def build_error_note(stage: str, e: Exception, ctx: Dict[str, Any]) -> str:
    ffmpeg = ctx.get("ffmpeg", "")
    ffprobe = ctx.get("ffprobe", "")
    note = [
        f"[단계] {stage}",
        f"[에러] {type(e).__name__}: {e}",
        f"[ffmpeg] {'OK' if (ffmpeg and Path(ffmpeg).is_file()) or (shutil.which('ffmpeg') is not None) else 'X'} ({ffmpeg or 'not set'})",
        f"[ffprobe] {'OK' if (ffprobe and Path(ffprobe).is_file()) or (shutil.which('ffprobe') is not None) else 'X'} ({ffprobe or 'not set'})",
        f"[행] {ctx.get('row','')}",
        f"[voice_id] {ctx.get('voice_id','')}",
        f"[model_id] {ctx.get('model_id','')}",
        f"[target_sec] {ctx.get('target_sec','')}",
        f"[voice_settings] {ctx.get('voice_settings','')}",
        f"\n[Trace tail]\n{_tail(traceback.format_exc(), 10)}"
    ]
    return clamp_note("\n".join(note))


# =============================================================================
# 시트(B17~B23) -> ElevenLabs voice_settings 파싱 유틸
# =============================================================================
def _to_float_or_none(s: str) -> Optional[float]:
    s = _clean(s)
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None

def _to_bool_or_none(s: str) -> Optional[bool]:
    s = _clean(s).lower()
    if s == "":
        return None
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return None

def build_eleven_voice_settings_from_sheet(
    stability: str,
    similarity: str,
    style: str,
    speed: str,
    spk_boost: str,
):
    """
    시트 값(B19~B23)을 ElevenLabs voice_settings로 변환.
    비어 있으면 None 반환(= API 기본값 사용).
    """
    st = _to_float_or_none(stability)
    sim = _to_float_or_none(similarity)
    sty = _to_float_or_none(style)
    spd = _to_float_or_none(speed)
    sb  = _to_bool_or_none(spk_boost)

    if all(v is None for v in (st, sim, sty, spd, sb)):
        return None

    payload: Dict[str, Any] = {}
    if st is not None:  payload["stability"] = st
    if sim is not None: payload["similarity_boost"] = sim
    if sty is not None: payload["style"] = sty
    if spd is not None: payload["speed"] = spd
    if sb is not None:  payload["use_speaker_boost"] = sb

    # VoiceSettings가 있으면 사용하되, 버전 차로 인한 TypeError는 dict로 fallback
    if VoiceSettings is not None:
        try:
            return VoiceSettings(**payload)
        except TypeError:
            return payload

    return payload


# =============================================================================
# ElevenLabs TTS
# =============================================================================
def eleven_tts_to_file(
    text: str,
    voice_id: str,
    out_audio: Path,
    model_id: str,
    voice_settings=None,
) -> Path:
    """
    ElevenLabs TTS → 오디오 스트림 저장
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("개별스크립트설정 텍스트가 비어 있습니다.")

    out_audio.parent.mkdir(parents=True, exist_ok=True)

    kwargs: Dict[str, Any] = dict(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format=ELEVEN_OUTPUT_FORMAT,
    )
    if voice_settings is not None:
        kwargs["voice_settings"] = voice_settings

    audio_stream = eleven.text_to_speech.convert(**kwargs)

    with open(out_audio, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)

    if not out_audio.exists() or out_audio.stat().st_size == 0:
        raise RuntimeError("ElevenLabs TTS 결과 파일이 비어 있습니다.")

    return out_audio


def ffmpeg_convert_to_wav(in_audio: Path, out_wav: Path, ffmpeg_path: Optional[str] = None) -> Path:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg 미설치: FFMPEG_PATH 또는 PATH 확인")

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-i", str(in_audio), "-ac", "1", "-ar", "44100", str(out_wav)]
    subprocess.run(cmd, check=True)
    return out_wav


def _atempo_chain(factor: float) -> str:
    """
    ffmpeg atempo는 0.5~2.0 범위.
    factor(tempo) 를 체인으로 분해.
    """
    if factor <= 0:
        raise ValueError("atempo factor must be > 0")

    parts = []
    f = factor
    while f < 0.5:
        parts.append(0.5)
        f /= 0.5
    while f > 2.0:
        parts.append(2.0)
        f /= 2.0
    parts.append(f)
    return ",".join([f"atempo={p:.8f}" for p in parts])


def stretch_audio_to_target(in_wav: Path, target_sec: float, out_wav: Path, ffmpeg_path: Optional[str] = None) -> Path:
    """
    1) pyrubberband 로 stretch 시도
    2) 실패하면 ffmpeg atempo 로 fallback
    """
    if target_sec <= 0:
        raise ValueError("target_sec 는 0보다 커야 합니다.")

    # 원본 길이
    try:
        y, sr = librosa.load(str(in_wav), sr=None, mono=True)
        orig_sec = float(librosa.get_duration(y=y, sr=sr))
    except Exception as e:
        raise RuntimeError(f"오디오 로드 실패: {e}")

    if orig_sec <= 0.01:
        raise RuntimeError("원본 오디오 길이가 비정상적으로 짧습니다.")

    # 거의 동일하면 그대로 복사
    if abs(orig_sec - target_sec) < 0.05:
        shutil.copy2(str(in_wav), str(out_wav))
        return out_wav

    # rubberband: rate = orig / target
    rate = orig_sec / target_sec

    try:
        y_st = pyrb.time_stretch(y, sr, rate)

        # 부드러운 페이드
        fade = int(0.05 * sr)
        if fade > 0 and len(y_st) > 2 * fade:
            ramp = np.linspace(0, 1, fade)
            y_st[:fade] *= ramp
            y_st[-fade:] *= ramp[::-1]

        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_wav), y_st, sr)
        return out_wav

    except Exception:
        # ffmpeg atempo fallback (tempo = target/orig)
        ffmpeg = ffmpeg_path or find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("rubberband 실패 + ffmpeg 미설치로 fallback 불가")

        tempo = target_sec / orig_sec
        chain = _atempo_chain(tempo)
        out_wav.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            ffmpeg, "-y",
            "-i", str(in_wav),
            "-filter:a", chain,
            "-ac", "1", "-ar", "44100",
            str(out_wav)
        ]
        subprocess.run(cmd, check=True)
        return out_wav


def make_mp4_from_audio(audio_wav: Path, target_sec: float, out_mp4: Path, ffmpeg_path: Optional[str] = None) -> Path:
    """
    검정 배경 영상 + 오디오로 MP4 생성
    """
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg 미설치: FFMPEG_PATH 또는 PATH 확인")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={VIDEO_SIZE}:r={VIDEO_FPS}:d={target_sec}",
        "-i", str(audio_wav),
        "-shortest",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True)
    return out_mp4


# =============================================================================
# 이메일
# =============================================================================
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def parse_email_list(s: str) -> List[str]:
    if not s:
        return []
    raw = re.split(r"[,\s;]+", s.strip())
    out = []
    for x in raw:
        x = x.strip()
        if not x:
            continue
        if _EMAIL_RE.fullmatch(x):
            out.append(x)
    seen = set()
    uniq = []
    for e in out:
        if e not in seen:
            uniq.append(e)
            seen.add(e)
    return uniq

def send_email_with_attachment(
    subject: str,
    body: str,
    to_list: List[str],
    cc_list: List[str],
    bcc_list: List[str],
    reply_to: Optional[str],
    attachment_path: Path,
):
    if not to_list and not cc_list and not bcc_list:
        raise RuntimeError("이메일 수신자(TO/CC/BCC)가 비어 있습니다. (시트 B11~B13 확인)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    if to_list:
        msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()

    msg.set_content(body)

    data = attachment_path.read_bytes()
    filename = attachment_path.name
    msg.add_attachment(data, maintype="video", subtype="mp4", filename=filename)

    recipients = to_list + cc_list + bcc_list

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg, from_addr=SMTP_USER, to_addrs=recipients)


# =============================================================================
# 메인 처리
# =============================================================================
def process() -> List[int]:
    sh = gc.open_by_url(SPREADSHEET_LINK)
    ws = sh.worksheet(SHEET_NAME)

    all_values = ws.get_all_values()
    total_rows = len(all_values)

    if total_rows < HEADER_ROW:
        raise RuntimeError("시트 행 수가 너무 적습니다. (헤더 4행 확인)")

    header = all_values[HEADER_ROW - 1]
    header_map = {h: i + 1 for i, h in enumerate(header) if (h or "").strip()}

    def idx(name: str) -> int:
        if name not in header_map:
            raise KeyError(f"시트에 '{name}' 열이 없습니다. (헤더 4행 기준)")
        return header_map[name]

    # 필수 컬럼
    col_sel   = idx("작업 선택")
    col_text  = idx("개별스크립트설정")
    col_len   = idx("영상길이")
    col_note  = idx("작업 비고") if "작업 비고" in header_map else None

    # 제목 구성용 컬럼
    col_old   = idx("기존작업일자") if "기존작업일자" in header_map else None
    col_vdate = idx("음성작업일자") if "음성작업일자" in header_map else None

    col_done_time = idx("작업 완료시간") if "작업 완료시간" in header_map else None

    def get_cell_from_cache(r: int, c: int) -> str:
        if r <= 0 or c <= 0:
            return ""
        if r - 1 >= len(all_values):
            return ""
        row = all_values[r - 1]
        if c - 1 >= len(row):
            return ""
        return _clean(row[c - 1])

    # =========================
    # ✅ ElevenLabs 설정: B17~B23
    # =========================
    voice_id_sheet = get_cell_from_cache(17, 2)
    model_id_sheet = get_cell_from_cache(18, 2)
    v_stability    = get_cell_from_cache(19, 2)
    v_similarity   = get_cell_from_cache(20, 2)
    v_style        = get_cell_from_cache(21, 2)
    v_speed        = get_cell_from_cache(22, 2)
    v_spk_boost    = get_cell_from_cache(23, 2)

    voice_id_effective = voice_id_sheet or ELEVEN_VOICE_ID_ENV
    if not voice_id_effective:
        raise RuntimeError("ElevenLabs voice_id가 없습니다. (시트 B17 또는 ELEVENLABS_VOICE_ID 설정 필요)")

    model_id_effective = model_id_sheet or ELEVEN_MODEL_ID_ENV or "eleven_multilingual_v2"

    voice_settings_effective = build_eleven_voice_settings_from_sheet(
        stability=v_stability,
        similarity=v_similarity,
        style=v_style,
        speed=v_speed,
        spk_boost=v_spk_boost,
    )

    # 이메일 주소: B11~B14
    to_raw   = get_cell_from_cache(11, 2)
    cc_raw   = get_cell_from_cache(12, 2)
    bcc_raw  = get_cell_from_cache(13, 2)
    rply_raw = get_cell_from_cache(14, 2)

    to_list  = parse_email_list(to_raw)
    cc_list  = parse_email_list(cc_raw)
    bcc_list = parse_email_list(bcc_raw)
    reply_to = parse_email_list(rply_raw)
    reply_to_one = reply_to[0] if reply_to else None

    ffmpeg_path = find_ffmpeg()
    ffprobe_path = find_ffprobe()

    dated_dir = DONE_ROOT / date.today().isoformat()
    dated_audio = dated_dir / "audio"
    dated_mp4   = dated_dir / "mp4"
    dated_tmp   = dated_dir / "tmp"
    for d in (dated_audio, dated_mp4, dated_tmp):
        d.mkdir(parents=True, exist_ok=True)

    processed_rows: List[int] = []
    error_batch: List[Dict] = []
    flush_every = 15

    # output_format이 mp3면 mp3로 저장, 아니면 bin으로 저장(후속 ffmpeg가 처리)
    def _tts_ext(fmt: str) -> str:
        f = (fmt or "").lower()
        if f.startswith("mp3"):
            return "mp3"
        if f.startswith("wav"):
            return "wav"
        if f.startswith("pcm"):
            return "pcm"
        return "bin"

    tts_ext = _tts_ext(ELEVEN_OUTPUT_FORMAT)

    for r in range(HEADER_ROW + 1, total_rows + 1):
        stage = "INIT"
        ctx: Dict[str, Any] = {
            "row": r,
            "ffmpeg": ffmpeg_path,
            "ffprobe": ffprobe_path,
            "voice_id": voice_id_effective,
            "model_id": model_id_effective,
            "voice_settings": str(voice_settings_effective) if voice_settings_effective is not None else "",
        }

        try:
            row = all_values[r - 1] if r - 1 < len(all_values) else []
            sel_val = _clean(row[col_sel - 1] if len(row) >= col_sel else "")
            if sel_val != "작업 시작":
                continue

            text = _clean(row[col_text - 1] if len(row) >= col_text else "")
            len_raw = _clean(row[col_len - 1] if len(row) >= col_len else "")

            if not text:
                raise ValueError("개별스크립트설정 값이 비어 있습니다.")
            if not len_raw:
                raise ValueError("영상길이 값이 비어 있습니다.")

            stage = "PARSE_DURATION"
            target_sec = parse_duration_to_sec(len_raw)
            ctx["target_sec"] = target_sec

            old_date = _clean(row[col_old - 1]) if (col_old and len(row) >= col_old) else ""
            voice_work_date = date.today().isoformat()

            first_line = text.splitlines()[0].strip() if text.splitlines() else text[:30]
            subject = f"{old_date} {voice_work_date} {first_line}".strip()
            subject = re.sub(r"\s+", " ", subject)

            base_name = sanitize_name(first_line, 60)
            stamp = datetime.now().strftime("%H%M%S")
            file_stub = sanitize_name(f"{base_name}_r{r}_{stamp}")

            # 1) Eleven TTS -> 오디오 파일
            stage = "ELEVEN_TTS"
            tts_path = dated_tmp / f"{file_stub}.{tts_ext}"
            eleven_tts_to_file(
                text=text,
                voice_id=voice_id_effective,
                out_audio=tts_path,
                model_id=model_id_effective,
                voice_settings=voice_settings_effective,
            )

            # 2) 오디오 -> wav
            stage = "AUDIO_TO_WAV"
            wav_raw = dated_tmp / f"{file_stub}_raw.wav"
            ffmpeg_convert_to_wav(tts_path, wav_raw, ffmpeg_path)

            # 3) stretch
            stage = "STRETCH"
            wav_st = dated_audio / f"{file_stub}_stretched.wav"
            stretch_audio_to_target(wav_raw, target_sec, wav_st, ffmpeg_path)

            # 4) wav -> mp4
            stage = "MAKE_MP4"
            out_mp4 = dated_mp4 / f"{file_stub}.mp4"
            make_mp4_from_audio(wav_st, target_sec, out_mp4, ffmpeg_path)

            # 5) 이메일 발송
            stage = "SEND_EMAIL"
            note_lines = [
                "[완료] ElevenLabs TTS → Stretch → MP4 생성",
                f"- voice_id: {voice_id_effective}",
                f"- model_id: {model_id_effective}",
                f"- voice_settings: {voice_settings_effective if voice_settings_effective is not None else '(default)'}",
                f"- output_format: {ELEVEN_OUTPUT_FORMAT}",
                f"- target_sec: {target_sec}",
                f"- mp4: {out_mp4.resolve()}",
                f"- 생성시간: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
                f"- 수신자: TO={','.join(to_list) or '-'} / CC={','.join(cc_list) or '-'} / BCC={','.join(bcc_list) or '-'}",
            ]
            note = "\n".join(note_lines)

            body = "\n".join([
                "아래 음성 작업 결과를 전달드립니다.",
                "",
                f"- 기존작업일자: {old_date or '-'}",
                f"- 음성작업일자: {voice_work_date}",
                "",
                "[개별스크립트설정]",
                text,
                "",
                "[작업 비고]",
                note,
                "",
            ])

            send_email_with_attachment(
                subject=subject,
                body=body,
                to_list=to_list,
                cc_list=cc_list,
                bcc_list=bcc_list,
                reply_to=reply_to_one,
                attachment_path=out_mp4,
            )

            # 6) 시트 업데이트
            stage = "SHEET_UPDATE"
            updates: List[Dict] = []

            if col_note:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_note),
                    "values": [[clamp_note(note)]],
                })

            if col_vdate:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_vdate),
                    "values": [[voice_work_date]],
                })

            if col_done_time:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_done_time),
                    "values": [[datetime.now().strftime("%Y/%m/%d %H:%M")]],
                })

            updates.append({
                "range": gspread.utils.rowcol_to_a1(r, col_sel),
                "values": [[NEXT_STATUS_AFTER_SUCCESS]],
            })

            safe_batch_update(ws, updates)
            processed_rows.append(r)

        except Exception as e:
            note = build_error_note(stage, e, ctx)

            if col_note:
                error_batch.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_note),
                    "values": [[note]],
                })
            error_batch.append({
                "range": gspread.utils.rowcol_to_a1(r, col_sel),
                "values": [["작업 중 에러"]],
            })

            if len(error_batch) >= flush_every:
                try:
                    safe_batch_update(ws, error_batch)
                finally:
                    error_batch.clear()

            continue

    if error_batch:
        safe_batch_update(ws, error_batch)

    print("✅ 처리 완료")
    if processed_rows:
        print("처리된 행:", processed_rows)
    else:
        print("이번 실행에서 처리된 행이 없습니다. ('작업 선택' == '작업 시작' 없음)")

    return processed_rows


if __name__ == "__main__":
    process()
