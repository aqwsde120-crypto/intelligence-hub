# 종근당 QA Intelligence Hub

## 사전 준비

1. **Supabase 프로젝트 생성** → URL과 anon key 복사
2. **Supabase SQL Editor**에서 `app/database/schema.sql` 실행
3. **Google Gemini API 키** 발급 (https://aistudio.google.com)

## 로컬 실행

```bash
git clone https://github.com/your-org/ckd-qa-hub
cd ckd-qa-hub
pip install -r requirements.txt
cp .env.example .env   # .env 파일에 키 입력
streamlit run Home.py
```

## Streamlit Community Cloud 배포

1. GitHub에 저장소 Push
2. https://share.streamlit.io → New app → 저장소 선택
3. Secrets 탭에서 환경변수 입력:
   ```
   SUPABASE_URL = "..."
   SUPABASE_KEY = "..."
   GEMINI_API_KEY = "..."
   ```

## GitHub Actions Secrets 설정

Settings → Secrets and variables → Actions에서 아래 3개 등록:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GEMINI_API_KEY`

## 수동 데이터 수집

```bash
python scripts/run_weekly.py
```
