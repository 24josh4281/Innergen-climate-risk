"""
flood_CHN (11.1 GB) 이어받기 다운로드
연결이 끊겨도 이어받기로 재시도
"""
import requests
import time
from pathlib import Path

URL = "https://data.iac.ethz.ch/climada/71f1304a-1b0a-444a-bb33-ff28f02b7833/flood_CHN.hdf5"
DEST = Path("c:/Users/24jos/climada/data/hazard/flood/flood_CHN/v1/flood_CHN.hdf5")
DEST.parent.mkdir(parents=True, exist_ok=True)

TOTAL_SIZE = 11918446781  # 11.1 GB
CHUNK = 8 * 1024 * 1024   # 8 MB chunk

def human_size(b):
    for u in ['B', 'KB', 'MB', 'GB']:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def download_with_resume(url, dest, total_size):
    attempt = 0
    while True:
        attempt += 1
        existing = dest.stat().st_size if dest.exists() else 0

        if existing >= total_size:
            print(f"이미 완료됨: {human_size(existing)}")
            return True

        headers = {'Range': f'bytes={existing}-'} if existing > 0 else {}
        if existing > 0:
            print(f"\n[시도 {attempt}] 이어받기: {human_size(existing)} / {human_size(total_size)} ({existing/total_size*100:.1f}%)")
        else:
            print(f"\n[시도 {attempt}] 새로 시작")

        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=60)
            if resp.status_code not in (200, 206):
                print(f"HTTP 오류: {resp.status_code}")
                time.sleep(10)
                continue

            mode = 'ab' if existing > 0 and resp.status_code == 206 else 'wb'
            if mode == 'wb':
                existing = 0  # 서버가 이어받기 미지원시 처음부터

            downloaded = existing
            start = time.time()
            last_print = time.time()

            with open(dest, mode) as f:
                for chunk in resp.iter_content(chunk_size=CHUNK):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_print >= 10:
                            elapsed = now - start
                            speed = (downloaded - existing) / elapsed / 1e6 if elapsed > 0 else 0
                            pct = downloaded / total_size * 100
                            print(f"  {pct:.1f}% ({human_size(downloaded)}) - {speed:.1f} MB/s", flush=True)
                            last_print = now

            final = dest.stat().st_size
            if final >= total_size:
                print(f"\n완료! {human_size(final)}")
                return True
            else:
                print(f"불완전: {human_size(final)} / {human_size(total_size)}")

        except Exception as e:
            print(f"오류: {e}")
            wait = min(30 * attempt, 300)
            print(f"{wait}초 후 재시도...")
            time.sleep(wait)

if __name__ == "__main__":
    print("flood_CHN.hdf5 다운로드 시작")
    print(f"대상: {DEST}")
    print(f"크기: {human_size(TOTAL_SIZE)}")
    download_with_resume(URL, DEST, TOTAL_SIZE)
