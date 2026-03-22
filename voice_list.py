import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# ✅ 현재 파이썬 파일과 같은 폴더의 .env를 확실히 로드
env_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=env_path, override=True)

def clean(s: str) -> str:
    return (s or "").strip().strip('"').strip("'").replace("\u200b","").replace("\ufeff","")

API_KEY = clean(os.getenv("ELEVENLABS_API_KEY"))

print("ENV PATH:", env_path)
print("API KEY LOADED:", bool(API_KEY), "LEN:", len(API_KEY))
if API_KEY:
    print("API KEY PREFIX/SUFFIX:", API_KEY[:6] + "..." + API_KEY[-4:])  # ✅ 일부만 표시

url = "https://api.elevenlabs.io/v1/voices"
r = requests.get(url, headers={"xi-api-key": API_KEY}, timeout=20)

print("STATUS:", r.status_code)
print("BODY:", r.text[:500])  # ✅ 에러 상세(앞부분만)
r.raise_for_status()

data = r.json()
for v in data.get("voices", []):
    print(v.get("name"), v.get("voice_id"), v.get("category"), v.get("labels"))
