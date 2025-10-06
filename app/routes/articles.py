from fastapi import APIRouter, HTTPException
import boto3
from datetime import datetime
import uuid
import requests
from app.modules.bedrock import call_bedrock_api, parse_bedrock_output
from app.modules.prompt_loader import load_prompt

router = APIRouter(prefix="/articles", tags=["Articles"])

# ✅ AWS 리소스
region = "us-east-1"
dynamodb = boto3.resource("dynamodb", region_name=region)
s3 = boto3.client("s3", region_name=region)

article_table = dynamodb.Table("ArticleTable")
news_table = dynamodb.Table("NewsTable")

# ✅ 업로드할 S3 버킷명
TARGET_BUCKET = "sayart-news-thumbnails"


@router.post("/generate-news/{article_id}")
def generate_news_from_article(article_id: str):
    """기사 기반으로 뉴스 생성 + 이미지 S3 업로드 후 본문 삽입"""
    try:
        # 1️⃣ 원본 기사 조회
        res = article_table.get_item(Key={"articleId": article_id})
        if "Item" not in res:
            raise HTTPException(status_code=404, detail="Article not found")
        article = res["Item"]

        # 2️⃣ category 확인
        category = article.get("category")
        if not category:
            raise HTTPException(
                status_code=400,
                detail="해당 기사에는 category 정보가 없습니다. (News 생성 불가)"
            )

        # 3️⃣ 이미지가 존재하면 S3 업로드
        image_url = article.get("imageUrl")
        uploaded_s3_url = None

        if image_url:
            try:
                image_data = requests.get(image_url).content
                image_key = f"news_thumbs/{article_id}_{uuid.uuid4().hex[:8]}.jpg"
                s3.put_object(
                    Bucket=TARGET_BUCKET, 
                    Key=image_key, 
                    Body=image_data, 
                    ContentType="image/jpeg",
                    ),
                uploaded_s3_url = f"https://{TARGET_BUCKET}.s3.amazonaws.com/{image_key}"
            except Exception as e:
                print(f"⚠️ 이미지 업로드 실패: {e}")
                uploaded_s3_url = None

        # Load prompt template
        prompt_template = load_prompt("news_en_prompt")

        # Replace placeholders
        prompt = (
            prompt_template
            .replace("{{content}}", article.get("content", ""))
            .replace("{{image_url}}", article.get("imageUrl") or "")
        )

        # Bedrock 호출
        result = call_bedrock_api(prompt=prompt, model_name="haiku-3.5")

        text = result["content"][0]["text"] if "content" in result else str(result)
        title, description = parse_bedrock_output(text)

        if not title or not description:
            raise HTTPException(
                status_code=500,
                detail="모델 출력 파싱 실패 — <Title> 또는 <Article> 태그가 누락되었습니다."
            )

        # 5️⃣ 이미지가 있으면 본문에 <img> 태그 추가
        if uploaded_s3_url:
            description = f'<img src="{uploaded_s3_url}" alt="기사 이미지" class="article-image"/>\n\n{description}'

        # 6️⃣ 새 뉴스 저장
        new_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        news_table.put_item(
            Item={
                "articleId": new_id,
                "title": title,
                "description": description,
                "sourceArticleId": article_id,
                "category": category,
                "pubDate": now,
                "author": "System",
                "imageUrl": uploaded_s3_url,  # ✅ 썸네일 URL 별도 저장
            }
        )

        return {
            "id": new_id,
            "title": title,
            "description": description,
            "category": category,
            "imageUrl": uploaded_s3_url,
            "createdAt": now,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
