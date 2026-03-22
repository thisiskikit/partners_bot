#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tts_ge.py (상태 기반 최종 버전)
- 처리 대상: '작업 선택' == 'TTS생성' 인 행만 처리
- 처리 성공 시: '작업 선택' → '이메일발송' (그리고 '작업 완료시간' 열이 있으면 타임스탬프 기록)
- 동작:
  1) '스크립트' → OpenAI TTS 생성 (모델=gpt-4o-mini-tts, 보이스=B8/B8 미지정 시 coral)
  2) 비디오 길이(ffprobe) 기반으로 부드럽게 stretch (rubberband)
  3) 원본('다운로드파일명') 영상에 새 오디오를 합쳐 done/YYYY-MM-DD/fin/fin_<파일명> 생성
  4) 원본 영상은 done/YYYY-MM-DD/org/org_<파일명> 으로 별도 보관
  5) 1초 지점 썸네일 thumb/<마지막세그먼트>.png 저장
- 오류 시 '작업 선택'='작업 중 에러', '작업 비고'에 상세 기록
- Google Sheets 429 대응: 읽기 최소화, 쓰기 시 안전 재시도(지수 백오프)
"""

import os, re, json, time, subprocess, shutil, traceback, random
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import librosa, soundfile as sf, pyrubberband as pyrb
import cv2
from PIL import Image

import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from openai import OpenAI, NotFoundError

# ── 환경
load_dotenv(dotenv_path='.env')
SPREADSHEET_LINK = os.getenv("SPREADSHEET_LINK") or ""
CREDS = os.getenv("CREDS_FILE_OHL1") or ""
OPENAI_KEY = os.getenv("openai.api_key") or ""
if not (SPREADSHEET_LINK and CREDS and OPENAI_KEY):
    raise RuntimeError("SPREADSHEET_LINK/CREDS_FILE_OHL2/openai.api_key 를 .env에 설정하세요.")

SHEET_NAME = "영상다운로드"
HEADER_ROW = 4
NEXT_STATUS_AFTER_TTS = os.getenv("TTS_NEXT_STATUS", "이메일발송")  # 필요 시 '작업완료'로 바꿔 사용

# PATH 보강 (ffprobe / rubberband)
script_dir = Path(__file__).resolve().parent
data_dir = script_dir / "data"
rb_dir   = data_dir / "rubberband"
os.environ["PATH"] = str(data_dir) + os.pathsep + os.environ.get("PATH", "")
os.environ["PATH"] = str(rb_dir)   + os.pathsep + os.environ.get("PATH", "")

# 클라이언트
client = OpenAI(api_key=OPENAI_KEY)
gs_creds = Credentials.from_service_account_file(CREDS, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(gs_creds)

# ── 유틸
MAX_NOTE_LEN = 1800
VALID_VOICES = {"alloy","aria","breeze","coral","verse","sage","opal","amber","stella"}

def sanitize_name(name: str, max_len: int = 100) -> str:
    import re as _re
    name = _re.sub(r"[\r\n]+", " ", name or "")
    name = _re.sub(r'[<>:"/\\|?*]', "_", name)
    return (name.strip() or "file")[:max_len]

def find_ffprobe() -> str:
    env_path = os.getenv("FFPROBE_PATH")
    if env_path and Path(env_path).is_file(): return str(Path(env_path))
    local = script_dir / "data" / "ffprobe.exe"
    if local.is_file(): return str(local)
    which = shutil.which("ffprobe")
    return which or ""

def get_video_duration(video_path: Path, ffprobe_path: Optional[str]) -> float:
    ffprobe = ffprobe_path or find_ffprobe()
    if not ffprobe:
        raise FileNotFoundError("ffprobe 미설치: FFPROBE_PATH 또는 ./data/ffprobe.exe 확인")
    cmd = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(res.stdout)["format"]["duration"])

def get_video_codec(video_path: Path, ffprobe_path: Optional[str]) -> Tuple[str, str]:
    ffprobe = ffprobe_path or find_ffprobe()
    if not ffprobe:
        raise FileNotFoundError("ffprobe 미설치: FFPROBE_PATH 또는 ./data/ffprobe.exe 확인")
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,codec_tag_string",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout or "{}")
    streams = info.get("streams") or []
    if not streams:
        return "", ""
    stream = streams[0] or {}
    codec_name = str(stream.get("codec_name") or "").strip().lower()
    codec_tag = str(stream.get("codec_tag_string") or "").strip().lower()
    return codec_name, codec_tag

def generate_tts(text: str, model: str, voice: str = "coral") -> Path:
    out = Path("narration_raw.wav")
    with client.audio.speech.with_streaming_response.create(
        model=model, voice=voice, input=text, response_format="wav"
    ) as resp:
        resp.stream_to_file(out)
    return out

def smooth_time_stretch(raw_path: Path, target_sec: float) -> Path:
    y, sr = librosa.load(str(raw_path), sr=None)
    orig = max(0.001, librosa.get_duration(y=y, sr=sr))
    rate = orig / max(0.001, target_sec)
    y_st = pyrb.time_stretch(y, sr, rate)
    fade = int(0.05 * sr)
    if fade > 0 and len(y_st) > 2 * fade:
        ramp = np.linspace(0, 1, fade)
        y_st[:fade] *= ramp
        y_st[-fade:] *= ramp[::-1]
    out = Path("narration_smooth.wav")
    sf.write(str(out), y_st, sr)
    return out

def _tail(tb: str, n: int = 8) -> str:
    return "\n".join(tb.strip().splitlines()[-n:])

def build_error_note(stage: str, e: Exception, ctx: Dict[str, Any]) -> str:
    ffp = ctx.get("ffprobe_path", "")
    codec_name = ctx.get("video_codec", "")
    codec_tag = ctx.get("video_codec_tag", "")
    note = [
        f"[단계] {stage}",
        f"[에러] {type(e).__name__}: {e}",
        f"[ffprobe] {'OK' if (ffp and Path(ffp).is_file()) or (shutil.which('ffprobe') is not None) else 'X'}",
        f"[ffprobe path] {ffp or '(not set)'}",
        f"[video codec] name={codec_name or '-'} tag={codec_tag or '-'}",
        f"[링크] {ctx.get('link','')}",
        f"[파일] {ctx.get('video_file','')}",
        f"\n[Trace tail]\n{_tail(traceback.format_exc(), 8)}"
    ]
    s = "\n".join(note)
    return s[:MAX_NOTE_LEN] + ("\n…(truncated)" if len(s) > MAX_NOTE_LEN else "")

# ── gspread 안전 쓰기 (429/5xx 백오프)
def safe_batch_update(ws, batch: List[Dict], max_attempts: int = 6):
    if not batch:
        return
    base = 1.2
    for attempt in range(1, max_attempts + 1):
        try:
            ws.batch_update(batch)
            return
        except APIError as e:
            msg = str(e)
            if any(c in msg for c in ("429","500","502","503","504")) and attempt < max_attempts:
                sleep_s = min(15.0, (base ** (attempt - 1))) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                continue
            raise

_read_last_ts = 0.0

def _is_transient_api_error(e: Exception) -> bool:
    msg = str(e)
    return any(code in msg for code in ("429", "500", "502", "503", "504"))

def _throttle_reads(min_interval: float = 0.35):
    global _read_last_ts
    now_t = time.monotonic()
    dt = now_t - _read_last_ts
    if dt < min_interval:
        time.sleep(min_interval - dt)
    _read_last_ts = time.monotonic()

def safe_batch_get(ws, ranges: List[str], max_attempts: int = 7):
    base = 1.7
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.batch_get(ranges)
        except APIError as e:
            if _is_transient_api_error(e) and attempt < max_attempts:
                sleep_s = min(60.0, (base ** (attempt - 1))) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                continue
            raise

def safe_get_all_values(ws, max_attempts: int = 7):
    base = 1.7
    for attempt in range(1, max_attempts + 1):
        try:
            _throttle_reads()
            return ws.get_all_values()
        except APIError as e:
            if _is_transient_api_error(e) and attempt < max_attempts:
                sleep_s = min(60.0, (base ** (attempt - 1))) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                continue
            raise

# ── 메인 처리 (처리 행 반환)
def process(target_rows: Optional[List[int]] = None) -> List[int]:
    sh = gc.open_by_url(SPREADSHEET_LINK)
    ws = sh.worksheet(SHEET_NAME)

    # TTS 고정 모델/보이스 (B8 비어 있으면 coral)
    model_name = "gpt-4o-mini-tts"
    cfg = safe_batch_get(ws, [f"B8:B8", f"A{HEADER_ROW}:ZZ{HEADER_ROW}"]) or [[], []]
    voice_cell = ""
    if cfg and len(cfg) >= 1 and cfg[0] and cfg[0][0]:
        voice_cell = str(cfg[0][0][0] or "").strip()
    voice_name = voice_cell if voice_cell else "coral"

    header = cfg[1][0] if len(cfg) >= 2 and cfg[1] else []
    header = [str(x).strip() if x is not None else "" for x in header]
    while header and header[-1] == "":
        header.pop()
    def idx(name: str) -> int:
        if name not in header:
            raise KeyError(f"시트에 '{name}' 열이 없습니다.")
        return header.index(name) + 1

    col_script = idx("스크립트")
    col_fname  = idx("다운로드파일명")
    col_link   = idx("쿠팡파트너스링크") if "쿠팡파트너스링크" in header else None
    col_sel    = idx("작업 선택")
    col_note   = idx("작업 비고") if "작업 비고" in header else None
    col_done   = idx("작업 완료시간") if "작업 완료시간" in header else None

    # 디렉토리
    audio_dir = (script_dir / "audios"); audio_dir.mkdir(exist_ok=True)
    done_root = (script_dir / "done");   done_root.mkdir(exist_ok=True)
    thumb_dir = (script_dir / "thumb");  thumb_dir.mkdir(exist_ok=True)
    video_dir = (script_dir / "videos")

    # 읽기 1회
    all_values = safe_get_all_values(ws)
    total_rows = len(all_values)
    ffprobe_path = find_ffprobe()
    target_set = set(target_rows or [])

    # 배치 버퍼
    error_batch: List[Dict] = []
    ERROR_BATCH_FLUSH_EVERY = 20

    # 날짜 폴더
    dated_dir = (done_root / date.today().isoformat())
    fin_dir = dated_dir / "fin"
    org_dir = dated_dir / "org"
    fin_dir.mkdir(parents=True, exist_ok=True)
    org_dir.mkdir(parents=True, exist_ok=True)

    processed_rows: List[int] = []  # ★ 추가
    error_rows = 0

    for r in range(HEADER_ROW + 1, total_rows + 1):
        if target_set and r not in target_set:
            continue
        stage = "INIT"; ctx: Dict[str, Any] = {}
        try:
            row = all_values[r-1] if r-1 < len(all_values) else []

            # 처리 대상
            sel_val = (row[col_sel-1] if len(row) >= col_sel else "").strip()
            if sel_val != "TTS생성":
                continue

            script_text = (row[col_script-1] if len(row) >= col_script else "").strip()
            raw_name    = (row[col_fname-1]  if len(row) >= col_fname  else "").strip()
            link_url    = (row[col_link-1]   if (col_link and len(row) >= col_link) else "").strip()
            if not script_text or not raw_name:
                continue

            video_file = video_dir / raw_name
            ctx.update({"link": link_url, "video_file": str(video_file), "ffprobe_path": ffprobe_path})
            if not video_file.is_file():
                raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_file}")

            # 1) 썸네일
            stage = "CAPTURE_THUMB"
            last_seg = sanitize_name(link_url.rstrip("/").split("/")[-1] if link_url else Path(raw_name).stem)
            cap = cv2.VideoCapture(str(video_file))
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
            ok, frame = cap.read()
            if ok and frame is not None:
                thumb_path = thumb_dir / f"{last_seg}.png"
                Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(str(thumb_path))
            cap.release()

            # 2) TTS
            stage = "GENERATE_TTS"
            base_name = Path(raw_name).stem
            try:
                raw_wav = generate_tts(script_text, model=model_name, voice=voice_name)
            except NotFoundError:
                raw_wav = generate_tts(script_text, model=model_name, voice="coral")
            dest_wav = audio_dir / f"{base_name}.wav"
            raw_wav.replace(dest_wav)

            # 3) 길이 & stretch
            stage = "FFPROBE_DURATION"
            duration = get_video_duration(video_file, ffprobe_path)

            stage = "FFPROBE_VIDEO_CODEC"
            codec_name, codec_tag = get_video_codec(video_file, ffprobe_path)
            ctx["video_codec"] = codec_name
            ctx["video_codec_tag"] = codec_tag
            incompatible_codec = (codec_name in ("", "none", "unknown")) or (codec_tag == "bvc2")
            if incompatible_codec:
                raise RuntimeError(
                    f"비디오 코덱 비호환(codec={codec_name or '-'}, tag={codec_tag or '-'})"
                )

            stage = "AUDIO_STRETCH"
            smooth = smooth_time_stretch(dest_wav, duration)

            # 4) ffmpeg로 합성
            stage = "FFMPEG_MUX"
            out_file = fin_dir / f"fin_{raw_name}"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_file),
                "-i", str(smooth),
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(out_file)
            ]
            subprocess.run(cmd, check=True)

            # 5) 원본 보존
            try:
                orig_copy = org_dir / f"org_{Path(raw_name).name}"
                if not orig_copy.exists():
                    shutil.copy2(str(video_file), str(orig_copy))
            except Exception as ce:
                if col_note:
                    error_batch.append({
                        "range": gspread.utils.rowcol_to_a1(r, col_note),
                        "values": [[f"[참고] 원본 복사 실패: {type(ce).__name__}: {ce}"]],
                    })

            # 상태 전환은 배치 쓰기 성공만 신뢰하고, 리드백(ws.cell) 검증은 하지 않는다.
            # 리드백 검증은 행당 다수 read를 유발해 Read requests quota를 빠르게 소진한다.
            stage = "SHEET_STATUS_UPDATE"
            updates = [{
                "range": gspread.utils.rowcol_to_a1(r, col_sel),
                "values": [[NEXT_STATUS_AFTER_TTS]],
            }]
            if col_done:
                updates.append({
                    "range": gspread.utils.rowcol_to_a1(r, col_done),
                    "values": [[datetime.now().strftime("%Y/%m/%d %H:%M")]],
                })
            safe_batch_update(ws, updates)

            if error_batch and (len(error_batch) % ERROR_BATCH_FLUSH_EVERY == 0):
                safe_batch_update(ws, error_batch); error_batch.clear()

            processed_rows.append(r)  # ★ 추가 — 방금 처리한 행 기록

        except Exception as e:
            error_rows += 1
            note = build_error_note(stage, e, ctx)
            if col_note:
                error_batch.append({"range": gspread.utils.rowcol_to_a1(r, col_note), "values": [[note]]})
            if col_sel:
                error_batch.append({"range": gspread.utils.rowcol_to_a1(r, col_sel), "values": [["작업 중 에러"]]})
            if len(error_batch) >= ERROR_BATCH_FLUSH_EVERY:
                try:
                    safe_batch_update(ws, error_batch)
                finally:
                    error_batch.clear()
            continue

    # 남은 배치 flush
    if error_batch:
        safe_batch_update(ws, error_batch)

    if error_rows:
        print(f"⚠️ TTS 완료 (성공={len(processed_rows)}, 실패={error_rows})")
    else:
        print(f"✅ TTS + 오디오 교체 완료 (성공={len(processed_rows)})")
    return processed_rows  # ★ 추가 — 처리된 행 목록 반환

# 스크립트 단독 실행
if __name__ == "__main__":
    process()
