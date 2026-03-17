"""
CLIMADA Data API - China (CHN) 관련 데이터 전체 다운로드
대상 좌표: 34.7979°N, 117.2571°E (Zaozhuang, Shandong, China)
"""
import os
import sys
import time
from pathlib import Path
from climada.util.api_client import Client

# 다운로드 디렉토리
DOWNLOAD_DIR = Path("c:/Users/24jos/climada/data")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CHINA_KEYWORDS = ['CHN', 'China', '_CN_']

def is_china_relevant(dataset):
    name = dataset.name.upper()
    props = str(dataset.properties).upper()
    return any(k.upper() in name or k.upper() in props for k in CHINA_KEYWORDS)

def human_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def main():
    print("=" * 60)
    print("CLIMADA Data API - 중국(CHN) 데이터 다운로드")
    print("=" * 60)

    client = Client()
    print("\n데이터셋 목록 조회 중...")
    all_datasets = client.list_dataset_infos()

    # 중국 관련 + centroids 필터링
    china_datasets = [d for d in all_datasets if is_china_relevant(d)]
    centroid_datasets = [d for d in all_datasets if d.data_type.data_type == 'centroids']

    target_datasets = china_datasets + centroid_datasets

    total_size = sum(sum(f.file_size for f in d.files) for d in target_datasets)
    print(f"대상 데이터셋: {len(target_datasets)}개 ({human_size(total_size)})")
    print(f"  - 중국 관련: {len(china_datasets)}개")
    print(f"  - Centroids: {len(centroid_datasets)}개")
    print(f"\n저장 위치: {DOWNLOAD_DIR}")
    print("=" * 60)

    # 타입별 정렬
    from collections import defaultdict
    by_type = defaultdict(list)
    for d in target_datasets:
        by_type[d.data_type.data_type].append(d)

    success, failed = [], []
    total_downloaded = 0
    start_time = time.time()

    for dtype, datasets in sorted(by_type.items()):
        type_size = sum(sum(f.file_size for f in d.files) for d in datasets)
        print(f"\n[{dtype.upper()}] {len(datasets)}개 ({human_size(type_size)})")

        for i, dataset in enumerate(sorted(datasets, key=lambda x: x.name), 1):
            ds_size = sum(f.file_size for f in dataset.files)
            print(f"  [{i}/{len(datasets)}] {dataset.name} ({human_size(ds_size)}) ...", end=" ", flush=True)
            try:
                download_dir, downloaded_files = client.download_dataset(dataset, target_dir=DOWNLOAD_DIR)
                total_downloaded += ds_size
                elapsed = time.time() - start_time
                speed = total_downloaded / elapsed / 1e6 if elapsed > 0 else 0
                print(f"완료 (평균 {speed:.1f} MB/s)")
                success.append(dataset.name)
            except Exception as e:
                print(f"실패: {e}")
                failed.append((dataset.name, str(e)))

    # 결과 요약
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("다운로드 완료 요약")
    print("=" * 60)
    print(f"성공: {len(success)}개 ({human_size(total_downloaded)})")
    print(f"실패: {len(failed)}개")
    if failed:
        for name, err in failed:
            print(f"  - {name}: {err}")
    print(f"소요 시간: {elapsed/60:.1f}분")
    print(f"저장 위치: {DOWNLOAD_DIR}")

if __name__ == "__main__":
    main()
