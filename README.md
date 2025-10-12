# 작업시작




# ECR 생성
```
# AWS CLI 로그인 (리전 예: us-east-1)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 678005315499.dkr.ecr.us-east-1.amazonaws.com

# ECR 리포지토리 생성
aws ecr create-repository --repository-name fastapi-apprunner

# 이미지 태그 변경
docker tag fastapi-apprunner:latest 678005315499.dkr.ecr.us-east-1.amazonaws.com/fastapi-apprunner:latest

```


# 이미지 푸시
docker build -t 678005315499.dkr.ecr.us-east-1.amazonaws.com/fastapi-apprunner .
docker push 678005315499.dkr.ecr.us-east-1.amazonaws.com/fastapi-apprunner:latest

