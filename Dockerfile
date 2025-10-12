# 베이스 이미지
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY ./app ./app

# 포트 지정
EXPOSE 8080

# FastAPI 실행 (포트 8080 필수)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
