# 배포 가이드 — Climate Risk Web

## 1. 사전 준비 (로컬 1회)

```bash
# CMIP6 그리드 데이터 생성 (이미 완료 시 생략)
python scripts/build_web_data.py
# 출력: api/data/cmip6_grid_east_asia.json (2.8MB)
#       api/data/cmip6_grid_global.json (15.6MB)
#       api/data/cmip6_sites.csv
#       api/data/physrisk_sites.csv
```

## 2. GitHub 리포지토리

1. GitHub에서 새 리포: `climate-risk-web`
2. `web/`, `api/` 폴더 전체 + `api/data/` 포함 push
   ```bash
   git add web/ api/ scripts/
   git commit -m "climate-risk-web: initial deploy"
   git push
   ```

## 3. Render.com 백엔드 배포

1. [render.com](https://render.com) → New Web Service
2. GitHub 리포 연결
3. 설정:
   - **Root Directory**: `api`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Region**: Singapore (Asia 지연 최소화)
   - **Plan**: Free
4. 배포 후 URL 확인 (예: `https://climate-risk-api.onrender.com`)

## 4. netlify.toml 업데이트

`web/netlify.toml`에서 Render URL 교체:
```toml
to = "https://[YOUR-RENDER-URL]/api/:splat"
```

## 5. Netlify 프론트엔드 배포

1. [netlify.com](https://netlify.com) → New site from Git
2. GitHub 리포 연결
3. 설정:
   - **Publish directory**: `web`
   - **Build command**: (없음 — 정적 사이트)
4. 배포 → 자동 HTTPS URL 생성

## 6. E2E 테스트 체크리스트

- [ ] T1: 기존 사이트 선택 → 10초 내 결과
- [ ] T2: 좌표 36.0, 128.5 입력 → 20초 내 결과, T2 배지
- [ ] T3: 런던 (51.5, -0.1) → 30초 내 결과, T3 배지
- [ ] 주소 검색: "포항시 남구" → T1 결과
- [ ] Excel 다운로드 → 파일 열기, Tier_Info 시트 확인

## 로컬 개발

```bash
# 백엔드
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프론트엔드 (브라우저에서 직접 열기)
# web/index.html → netlify.toml 프록시가 없으므로 api.js에서 BASE_URL 수동 변경:
# const API_BASE = "http://127.0.0.1:8000/api";
```
