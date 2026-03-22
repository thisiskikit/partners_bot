# -*- coding: utf-8 -*-
import os
import io
import base64
import cv2
from PIL import Image
from openai import OpenAI
import re
import numpy as np

from dotenv import load_dotenv
load_dotenv()  # .env에서 CREDS_FILE_OHL1 로드

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError
import gspread.utils

import hmac
import hashlib
import requests
from datetime import datetime, timezone
import time

# ────────────────────────────────────────────────────────────────
# OpenAI / Coupang 설정 (키 정리 + 필수 검사)
def _clean(s: str) -> str:
    return (s or "").strip().strip('"').strip("'").replace("\u200b","").replace("\ufeff","")

OPENAI_KEY = _clean(os.getenv("openai.api_key"))
if not OPENAI_KEY:
    raise RuntimeError("openai.api_key 환경변수가 설정되지 않았습니다.")
client = OpenAI(api_key=OPENAI_KEY)

ACCESS_KEY = _clean(os.getenv("COUPANG_ACCESS"))
SECRET_KEY = _clean(os.getenv("COUPANG_SECRET"))
SUB_ID     = _clean(os.getenv("COUPANG_SUB_ID") or "")
if not ACCESS_KEY or not SECRET_KEY:
    raise RuntimeError("COUPANG_ACCESS / COUPANG_SECRET 환경변수를 설정하세요.")

DOMAIN     = "https://api-gateway.coupang.com"
API_PREFIX = "/v2/providers/affiliate_open_api/apis/openapi/v1"

# ────────────────────────────────────────────────────────────────
# Coupang: 서명/요청 (파트너스 전용 HMAC)
def generate_hmac(method: str, path: str, query: str = "") -> str:
    """
    Coupang Partners 요구 포맷
    - signed-date: yyMMdd'T'HHmmss'Z' (2자리 연도)
    - Authorization: 콤마 뒤 공백 없음
    - 서명 메시지: signed-date + METHOD + path + (query에서 '?' 제거한 문자열)
    """
    method = (method or "").upper().strip()
    if not path.startswith("/"):
        raise ValueError(f"path는 절대경로여야 합니다: {path}")
    q_for_sign = query[1:] if (query and query.startswith("?")) else (query or "")

    signed_date = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    message = f"{signed_date}{method}{path}{q_for_sign}"
    signature = hmac.new(SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    # 콤마 뒤 공백 없음 (중요)
    return (
        "CEA "
        f"algorithm=HmacSHA256,access-key={ACCESS_KEY},"
        f"signed-date={signed_date},signature={signature}"
    )

def convert_to_affiliate_link(coupang_url: str, sub_id: str = "") -> dict:
    path = f"{API_PREFIX}/deeplink"
    full_url = DOMAIN + path
    body = {"coupangUrls": [coupang_url]}
    if sub_id:
        body["subId"] = sub_id

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": generate_hmac("POST", path, ""),
    }
    max_attempts, base = 5, 1.7
    last_err = None

    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(full_url, headers=headers, json=body, timeout=10)
            if resp.status_code >= 400:
                try:
                    j = resp.json()
                except Exception:
                    j = {"text": resp.text}
                raise RuntimeError(f"HTTP {resp.status_code} {j}")
            return resp.json()
        except Exception as e:
            last_err = e
            msg = str(e)
            transient = any(t in msg for t in ("429","500","502","503","504","timeout"))
            if not transient or attempt >= max_attempts:
                raise
            sleep_s = min(30.0, (base ** (attempt - 1))) + 0.2 * attempt
            time.sleep(sleep_s)
    raise last_err or RuntimeError("Unknown deeplink error")

def affiliate_search_fallback(keyword: str, sub_id: str = "") -> str:
    """
    딥링크 실패 시 products/search로 대체 링크 생성
    - GET 서명 시 query는 '?...'를 만들되, 서명에는 '?' 제거 규칙을 generate_hmac가 처리
    """
    path = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
    q = f"?keyword={requests.utils.quote(keyword, safe='')}&limit=1"
    if sub_id:
        q += f"&subId={requests.utils.quote(sub_id, safe='')}"
    url = DOMAIN + path + q
    headers = {
        "Authorization": generate_hmac("GET", path, q),
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    j = r.json()
    data = j.get("data") or []
    if not data:
        return ""
    d0 = data[0] or {}
    return d0.get("productUrl") or d0.get("landingUrl") or ""

# ────────────────────────────────────────────────────────────────
# 비디오 유틸

def get_video_duration(path: str) -> float:
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_cnt = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return frame_cnt / fps

# ────────────────────────────────────────────────────────────────
# 3) 씬 디텍션

def detect_scenes(path: str, hist_thresh: float = 0.2, step_sec: float = 0.5):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = int(fps * step_sec)
    scenes, frame_idx, start_ts = [], 0, 0.0

    ret, prev = cap.read()
    if not ret:
        cap.release()
        return []
    prev_hist = cv2.calcHist([prev], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
    prev_hist = cv2.normalize(prev_hist, None).flatten()

    while True:
        frame_idx += step
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            end_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            scenes.append((start_ts, end_ts, prev))
            break

        curr_hist = cv2.calcHist([frame], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        curr_hist = cv2.normalize(curr_hist, None).flatten()
        diff = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_BHATTACHARYYA)

        if diff > hist_thresh:
            end_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            scenes.append((start_ts, end_ts, prev))
            start_ts = end_ts

        prev_hist, prev = curr_hist, frame

    cap.release()
    return scenes

# ────────────────────────────────────────────────────────────────
# 4) 짧은 씬 병합

def merge_short_scenes(scenes, min_duration: float = 1.0):
    if not scenes:
        return []
    merged = []
    cur_s, cur_e, cur_f = scenes[0]
    for s, e, f in scenes[1:]:
        dur = cur_e - cur_s
        if dur < min_duration:
            cur_e = e
        else:
            merged.append((cur_s, cur_e, cur_f))
            cur_s, cur_e, cur_f = s, e, f
    merged.append((cur_s, cur_e, cur_f))
    return merged

# ────────────────────────────────────────────────────────────────
# 5) GPT 비전: 씬 설명

def describe_scene(frame_bgr: np.ndarray, product_info: str) -> str:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="JPEG", quality=50, optimize=True)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    prompt = (
        f"이 이미지는 『{product_info}』 숏츠 광고의 한 장면입니다.\n\n"
        f"![scene](data:image/jpeg;base64,{img_b64})\n\n"
        "① 제품의 어떤 부분이 강조되는지 ② 배경 상황 ③ 후킹 포인트까지, "
        "구어체로 1문장(20자 내외)으로 설명해 주세요."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

# ────────────────────────────────────────────────────────────────
# 6) 전체 영상 요약

def describe_overall_video(scene_texts, total_sec: float, product_info: str) -> str:
    lines = [f"{int(s)}-{int(e)}초: {t}" for (s, e), t in scene_texts]
    prompt = (
        f"당신은 『{product_info}』 숏츠 콘텐츠 전문가입니다.\n"
        "■ 장면 요약 ■\n" + "\n".join(lines) +
        f"\n\n총 길이 {int(total_sec)}초, 이 숏츠가 전달하려는 핵심 메시지와 "
        "시청자에게 주는 가치를 1문장 내외로 요약해 주세요."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

# ────────────────────────────────────────────────────────────────
# 7) 마케팅 요소 생성

def generate_coupang_keywords(product_info: str) -> str:
    prompt = (
        f"제품 '{product_info}'에 대해, 핵심 키워드인 '{product_info}'를 참고하여\n"
        "쿠팡에서 실제 이용자가 검색할 만한 **상세 검색 키워드** 1개를\n"
        "만들어주세요."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def generate_best_coupang_keyword(keywords: str) -> str:
    prompt = (
        "다음 쿠팡 검색 키워드 리스트에서 이 숏츠 영상에 가장 어울리는 키워드 하나만, "
        "디테일한 검색어로 하나만 출력해주세요.\n"
        f"{keywords}"
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def generate_target_audience(overall_summary: str) -> str:
    prompt = (
        "다음 영상 요약을 참고하여 이 숏츠 광고의 이상적인 타겟 고객(연령대, 성별, 관심사 등)을 "
        "한 문장으로 정의해주세요.\n" + overall_summary
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def generate_video_headline(product_info: str, overall_summary: str) -> str:
    prompt = (
        "아래 인스타그램 리일스 계정의 톤앤매너를 참고하세요:\n"
        "- 선명한 컬러 배경 위에 큼직한 한글 오버레이\n"
        "- 이모지로 감정 강조 (🌟✨🤣 등)\n"
        "- 짧고 강렬한 호기심 유발 문구\n\n"
        f"제품 '{product_info}' 숏츠 광고에 딱 맞는 4~15자 이내의 자극적인 타이틀 5개를\n"
        f"전체 요약('{overall_summary}')을 반영해 생성해주세요.\n"
        "각 타이틀은 개행(\\n)으로 구분해 주세요."
    )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def generate_instagram_content(script: str, info_keyword: str, extra_prompt: str = "") -> str:
    base_prompt = (
        "아래 숏츠 광고 스크립트를 참고해서, 인스타그램 마케팅용으로\n"
        "— 2~10줄의 이모지를 섞은 감성 카피\n"
        "— 마지막에\n"
        f"💖 댓글에 [{info_keyword}] 남겨주시거나\n 💖 프로필 링크에서 [{info_keyword}] 검색!\n 🌟 팔로우 하고 보내주셔야 오류 없이 정상적으로 보내져요!\n"
        "을 꼭 붙여줘.\n"
        f"■ 숏츠 스크립트 ■\n{script}"
    )
    if extra_prompt:
        base_prompt += (
            "\n\n[추가 가이드(B10)]\n"
            f"{extra_prompt}\n"
            "※ 위 추가 가이드는 기존 형식보다 선행해서 참고 하세요."
        )
    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": base_prompt}]
    )
    return resp.choices[0].message.content.strip()

# ────────────────────────────────────────────────────────────────
# 8) 최종 스크립트 생성

def build_final_script(scene_texts, total_sec: float, overall_summary: str,
                       target_audience: str, product_info: str,
                       extra_prompt: str = "",
                       reference_info: str = "") -> str:
    lines = [f"{int(s)}-{int(e)}초: {t}" for (s, e), t in scene_texts]
    ref_block = f"■ 참고정보 ■\n{reference_info}\n\n" if reference_info else ""

    base_prompt = (
        "당신은 SNS를 이용하는 현대인 대상으로 한 숏폼 광고 전문가입니다.\n"
        f"이 광고의 타겟: {target_audience}\n"
        f"■ 제품 요약 ■\n{overall_summary}\n\n"
        f"이 상품은 {ref_block}"
        "■ 장면별 설명 ■\n" + "\n".join(lines) +
        f"\n\n총 길이 {int(total_sec)}초, 1초에 최대 5자 내외, 반말 구어체, "
        "‼️ 줄 앞에 [0-2초] 같은 시간 구간을 절대 넣지 말고 순수 문장만 출력합니다.\n\n"
        "후킹 문구와 CTA 포함해 최대 10줄로 작성해주세요.\n\n"
        "프로필 링크 참고하셔~로 스크립트 마무리."
    )

    if extra_prompt:
        base_prompt += (
            "\n\n[추가 가이드(B9)]\n"
            f"{extra_prompt}\n"
            "※ 핵심 출력 형식(줄 수/톤/마침문구)보다 선행되어서 반영하세요."
        )

    resp = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": base_prompt}]
    )
    return resp.choices[0].message.content.strip()

def extract_info_keyword(text: str) -> str:
    tokens = re.findall(r'\w+', text)
    return max(tokens, key=len) if tokens else ''

# ────────────────────────────────────────────────────────────────
# 9) 길이 맞춤

def fit_script_length(
    text: str,
    max_chars: int,
    total_sec: float,
    target_audience: str,
    info_keyword: str,
    tol: float = 0.05
) -> str:
    min_chars = int(max_chars * (1 - tol))
    for _ in range(3):
        length = len(text.replace("\n", ""))
        if length > max_chars:
            prompt = (
                f"다음은 {int(total_sec)}초짜리 숏츠 광고에 들어갈 대본이야.\n"
                f"타깃은 {target_audience}고, 영상의 호응을 끌어야 해.\n"
                f"{min_chars}~{max_chars}자 사이로, 톤과 임팩트는 마치 Mr.Beats 가 광고하듯 "
                "마케팅 포인트를 살려서 축약해 줘.\n"
            )
        elif length < min_chars:
            prompt = (
                f"다음은 {int(total_sec)}초짜리 숏츠 광고 대본이야.\n"
                f"타깃은 {target_audience}, 영상 후킹을 위해 감탄사·호응어 쓸 수 있어.\n"
                f"{min_chars}~{max_chars}자 사이로 자연스럽게 톤과 임팩트는 마치 Mr.Beats 가 광고하듯 "
                "마케팅 포인트를 살려서 늘려 줘.\n"
            )
        else:
            break
        text = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content.strip()
    return text

# ────────────────────────────────────────────────────────────────
# 10) 시트 처리

def process_list_sheet(
    sheet_url: str,
    header_row: int
):
    creds_path = os.getenv('CREDS_FILE_OHL1')
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)
    ws = sh.worksheet('list')

    headers     = ws.row_values(header_row)
    idx         = {h: i+1 for i, h in enumerate(headers)}
    exec_col    = idx['실행버튼']
    file_col    = idx['작업파일명']
    kw_col      = idx['키워드']
    script_cols = [idx.get(str(i)) for i in range(1, 10+1)]
    combined    = idx['스크립트']
    partner_col = idx['쿠팡파트너스링크']
    insta_col   = idx['인스타글내용']
    sum_col     = idx['영상설명요약']
    search_col  = idx['검색용키워드']
    info_col    = idx['인포크키워드']
    title_col   = idx['타이틀']
    log_col     = idx['작업로그']
    len_col     = idx['영상길이']
    ref_col     = idx.get('참고정보')

    start_row = header_row + 1
    end_row   = ws.row_count
    a1_range  = f"{gspread.utils.rowcol_to_a1(start_row, exec_col)}:" \
                f"{gspread.utils.rowcol_to_a1(end_row, exec_col)}"
    exec_vals = ws.batch_get([a1_range])[0]
    target_rows = [
        start_row + i for i, cell in enumerate(exec_vals)
        if cell and cell[0] == '스크립트필요'
    ]
    extra_prompt_b9 = (ws.acell('B9').value or '').strip()
    extra_prompt_b10 = (ws.acell('B10').value or '').strip()

    for row in target_rows:
        if ws.cell(row, exec_col).value != '스크립트필요':
            continue

        keyword     = (ws.cell(row, kw_col).value or "").strip()
        filename    = ws.cell(row, file_col).value
        video_path  = os.path.join(os.getcwd(), 'videos', filename)

        if not os.path.exists(video_path):
            ws.update_cell(row, log_col, f"❌ 영상 파일 없음: {filename}")
            continue

        total_sec   = get_video_duration(video_path)
        scenes      = merge_short_scenes(detect_scenes(video_path))
        scene_texts = [((s, e), describe_scene(f, keyword)) for (s, e, f) in scenes]

        overall_summary = describe_overall_video(scene_texts, total_sec, keyword)
        target_audience = generate_target_audience(overall_summary)
        coupang_list    = generate_coupang_keywords(keyword)
        best_keyword    = generate_best_coupang_keyword(coupang_list)
        info_keyword    = extract_info_keyword(best_keyword)
        headline        = generate_video_headline(keyword, overall_summary)
        reference_info  = (ws.cell(row, ref_col).value or "").strip() if ref_col else ""

        script_text = build_final_script(
            scene_texts, total_sec, overall_summary, target_audience, keyword,
            extra_prompt=extra_prompt_b9,
            reference_info=reference_info
        )
        insta_content = generate_instagram_content(
            script_text, info_keyword, extra_prompt=extra_prompt_b10
        )

        max_chars = int(round(total_sec * 9))
        script_text = fit_script_length(
            script_text, max_chars, total_sec, target_audience, info_keyword
        )
        script_lines = script_text.splitlines()

        # 링크 생성(키워드가 비면 스킵)
        affiliate_link = ""
        if keyword:
            search_url = (
                "https://www.coupang.com/np/search"
                "?component=&q=" + requests.utils.quote(keyword, safe='') +
                "&channel=user"
            )
            try:
                result = convert_to_affiliate_link(search_url, SUB_ID)
                data = result.get("data") or []
                if data and isinstance(data, list):
                    d0 = data[0] or {}
                    affiliate_link = d0.get("shortenUrl") or d0.get("landingUrl") or ""
                # 딥링크가 비면 products/search로 우회
                if not affiliate_link:
                    affiliate_link = affiliate_search_fallback(keyword, SUB_ID) or ""
                    if not affiliate_link:
                        ws.update_cell(
                            row, log_col,
                            f"[Coupang] deeplink empty → products/search도 빈값: {result}"
                        )
            except Exception as e:
                affiliate_link = ""
                ws.update_cell(row, log_col, f"[Coupang] error: {type(e).__name__}: {e}")
        else:
            ws.update_cell(row, log_col, "[Coupang] keyword 비어 링크 생성 스킵")

        # batch_update 준비
        batch_data = []
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, sum_col),
                           'values': [[overall_summary]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, search_col),
                           'values': [[best_keyword]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, title_col),
                           'values': [[headline]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, partner_col),
                           'values': [[affiliate_link]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, info_col),
                           'values': [[info_keyword]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, len_col),
                           'values': [[round(total_sec, 2)]]})

        for i, col in enumerate(script_cols):
            if not col:
                continue
            text = script_lines[i] if i < len(script_lines) else ""
            batch_data.append({
                'range': gspread.utils.rowcol_to_a1(row, col),
                'values': [[text]]
            })

        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, combined),
                           'values': [[' '.join(script_lines)]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, insta_col),
                           'values': [[insta_content]]})
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, exec_col),
                           'values': [['TTS필요']]})

        prev = ws.cell(row, log_col).value or ''
        ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new  = (prev + '\n' + f"{ts} - 스크립트 생성") if prev else f"{ts} - 스크립트 생성"
        batch_data.append({'range': gspread.utils.rowcol_to_a1(row, log_col),
                           'values': [[new]]})

        done = False
        while not done:
            try:
                ws.batch_update(batch_data)
                done = True
            except APIError as e:
                if '429' in str(e):
                    print(f"429 발생, 1초 후 재시도… (row {row})")
                    time.sleep(1)
                else:
                    raise

        time.sleep(0.5)

    print("✅ ‘스크립트필요’ 행 모두 처리 완료!")

# ────────────────────────────────────────────────────────────────
# 11) 메인

def main():
    process_list_sheet(
        sheet_url="https://docs.google.com/spreadsheets/d/1x9qDs6dfEsykaGgCs8T8O0ftLz0EC3K0vVqLUx5jQJM/edit?gid=157812415",
        header_row=4
    )

if __name__ == "__main__":
    main()
