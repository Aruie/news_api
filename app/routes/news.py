from fastapi import APIRouter, HTTPException
import boto3
from boto3.dynamodb.conditions import Attr
import xml.etree.ElementTree as ET

router = APIRouter(
    prefix="/news",
    tags=["News Articles"]
)

# ✅ us-east-1 리전 DynamoDB (현재 구조)
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
news_table = dynamodb.Table("NewsTable")


@router.get("/category/{category}")
def get_articles_by_category(category: str):
    """
    ✅ 카테고리별 뉴스 목록 (pubDate 내림차순 정렬)
    """
    try:
        # GSI가 없기 때문에 scan + filter 사용
        response = news_table.scan(
            FilterExpression=Attr("category").eq(category)
        )
        items = response.get("Items", [])

        # pubDate 기준 내림차순 정렬
        items.sort(key=lambda x: x.get("pubDate", ""), reverse=True)

        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/article/{article_id}")
def get_article_detail(article_id: str):
    """
    ✅ 단일 뉴스 상세 조회
    """
    try:
        response = news_table.get_item(Key={"articleId": article_id})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail=f"Article not found: {article_id}")
        return response["Item"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
