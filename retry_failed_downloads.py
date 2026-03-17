"""
실패한 데이터셋 재시도 스크립트
"""
import time
from pathlib import Path
from climada.util.api_client import Client

DOWNLOAD_DIR = Path("c:/Users/24jos/climada/data")

FAILED_NAMES = [
    'earth_centroids_150asland_1800asoceans_distcoast_regions',
    'flood_CHN',
    'TC_CHN_0300as_STORM_EC-Earth3P-HR',
    'TC_CHN_0300as_STORM_HadGEM3-GC31-HM',
    'TC_TWN_0300as_STORM',
    'TC_TWN_0300as_STORM_CMCC-CM2-VHR4',
    'TC_TWN_0300as_STORM_CNRM-CM6-1-HR',
    'tropical_cyclone_0synth_tracks_150arcsec_historical_CHN_1980_2020',
]

def human_size(b):
    for u in ['B','KB','MB','GB']:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def main():
    print("=" * 60)
    print("실패한 데이터셋 재다운로드")
    print("=" * 60)

    client = Client()
    all_datasets = client.list_dataset_infos()
    targets = [d for d in all_datasets if d.name in FAILED_NAMES]

    print(f"재시도 대상: {len(targets)}개")
    total_size = sum(sum(f.file_size for f in d.files) for d in targets)
    print(f"총 용량: {human_size(total_size)}\n")

    success, failed = [], []
    start = time.time()

    for i, dataset in enumerate(sorted(targets, key=lambda x: sum(f.file_size for f in x.files)), 1):
        size = sum(f.file_size for f in dataset.files)
        print(f"[{i}/{len(targets)}] {dataset.name} ({human_size(size)}) ...", end=" ", flush=True)
        try:
            client.download_dataset(dataset, target_dir=DOWNLOAD_DIR)
            elapsed = time.time() - start
            print(f"완료 ({elapsed/60:.1f}분 경과)")
            success.append(dataset.name)
        except Exception as e:
            print(f"실패: {e}")
            failed.append((dataset.name, str(e)))

    print("\n" + "=" * 60)
    print(f"성공: {len(success)}개 / 실패: {len(failed)}개 / 소요: {(time.time()-start)/60:.1f}분")
    if failed:
        for name, err in failed:
            print(f"  ❌ {name}: {err[:80]}")

if __name__ == "__main__":
    main()
