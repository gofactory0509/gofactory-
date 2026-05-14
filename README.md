# 🎯 Go면접 면접 연습

AI 면접관과 함께하는 실전 면접 연습 서비스입니다.

## 주요 기능

- **직무별 면접 질문 생성**: 반도체, 백엔드, 데이터, 마케팅 등 직무에 맞는 질문
- **AI 답변 피드백**: 논리성, 핵심 키워드, 개선점을 구체적으로 분석
- **면접 기록 저장**: SQLite로 모든 면접 기록 자동 저장
- **기록 조회**: 이전 면접 기록을 직무별로 필터링하여 확인
- **오늘의 질문**: 매일 랜덤 면접 질문 제공

## 기술 스택

- **Frontend**: Streamlit
- **AI**: Google Gemini 2.0 Flash
- **Database**: SQLite
- **Deploy**: Streamlit Cloud

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 환경 변수

`.env` 파일에 Gemini API 키를 설정하세요:

```
GEMINI_API_KEY=your_api_key_here
```

또는 Streamlit Cloud Secrets에 설정할 수 있습니다.
