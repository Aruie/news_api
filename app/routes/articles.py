from fastapi import APIRouter, HTTPException
import boto3
import uuid
import requests
import re
from app.modules.bedrock import call_bedrock_api, parse_bedrock_output
from app.modules.prompt_loader import load_prompt  # ✅ 프롬프트 로더 import
from datetime import datetime

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
        res = article_table.get_item(Key={"articleId": article_id})
        if "Item" not in res:
            raise HTTPException(status_code=404, detail="Article not found")
        article = res["Item"]

        # 이미 생성된 뉴스가 있으면 중복 방지
        if article.get("generatedNewsId"):
            return {"message": "Already generated", "newsId": article["generatedNewsId"]}

        category = article.get("category")
        if not category:
            raise HTTPException(status_code=400, detail="Missing category info")

        # ✅ 이미지 업로드
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
                )
                uploaded_s3_url = f"https://{TARGET_BUCKET}.s3.amazonaws.com/{image_key}"
            except Exception as e:
                print(f"⚠️ 이미지 업로드 실패: {e}")

        # ✅ Bedrock 프롬프트 불러오기 (외부 텍스트 파일 기반)
        try:
            template = load_prompt("generate_news")  # app/modules/prompts/generate_news.txt
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prompt load failed: {e}")

        # ✅ 템플릿 변수 치환
        prompt = (
            template
            .replace("{{content}}", article.get("content", ""))
            .replace("{{image_url}}", uploaded_s3_url or image_url or "")
            .replace("{{article_url}}", article.get("articleUrl", ""))
        )

        # ✅ Bedrock 호출
        result = call_bedrock_api(prompt=prompt, model_name="haiku-3.5")
        text = result["content"][0]["text"] if "content" in result else str(result)
        title, description = parse_bedrock_output(text)
        
        

        if not title or not description:
            raise HTTPException(status_code=500, detail="Bedrock output parsing failed")
        
        description = re.sub(r'\n{2,}', '</p><p>', description.strip())
        description = f"<p>{description}</p>"

        # ✅ 이미지 캡션 - 실제 URL 사용
        # if uploaded_s3_url:
        #     source_link = article.get("articleUrl") or article.get("sourceUrl") or ""
        #     description = (
        #         f'<img src="{uploaded_s3_url}" alt="news image" class="article-image"/>'
        #         f'<p style="text-align:center;color:#666;font-size:0.85rem;">'
        #         f'Image courtesy of <a href="{source_link}" target="_blank" rel="noreferrer">{source_link}</a>'
        #         f'</p>\n\n{description}'
        #     )
        if uploaded_s3_url:
            article_name = article.get("srcName") or article.get("sourceId") or "Source"
            article_url = article.get("articleUrl") or article.get("sourceUrl") or ""

            description = (
                f'<img src="{uploaded_s3_url}" alt="news image" class="article-image"/>'
                f'<p style="text-align:center;color:#666;font-size:0.85rem;">'
                f'Image courtesy of {article_name} '
                f'<a href="{article_url}" target="_blank" rel="noreferrer" '
                f'style="text-decoration:none;">🔗</a>'
                f'</p>\n\n{description}'
            )


        # ✅ 새 뉴스 생성
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
                "imageUrl": uploaded_s3_url,
            }
        )

        # ✅ ArticleTable에 generatedNewsId 업데이트
        article_table.update_item(
            Key={"articleId": article_id},
            UpdateExpression="SET generatedNewsId = :nid",
            ExpressionAttributeValues={":nid": new_id},
        )

        return {
            "message": "Generated successfully",
            "id": new_id,
            "title": title,
            "description": description,
            "category": category,
            "imageUrl": uploaded_s3_url,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
