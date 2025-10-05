from fastapi import APIRouter, HTTPException
import boto3
from boto3.dynamodb.conditions import Key, Attr

router = APIRouter(
    prefix="/sources",
    tags=["Sources"]
)

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
source_table = dynamodb.Table("SourceMetaTable")
article_table = dynamodb.Table("ArticleTable")


@router.get("")
def get_all_sources():
    """모든 수집처 목록 조회"""
    try:
        response = source_table.scan()
        items = response.get("Items", [])
        return {"count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
def get_source_detail(source_id: str):
    """특정 수집처 상세 정보"""
    try:
        response = source_table.get_item(Key={"sourceId": source_id})
        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Source not found")
        return response["Item"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}/articles")
def get_articles_by_source(source_id: str):
    """특정 수집처의 기사 목록 조회"""
    try:
        # ✅ GSI 없음 → scan + filter로 대체
        response = article_table.scan(
            FilterExpression=Attr("sourceId").eq(source_id)
        )
        items = response.get("Items", [])
        return {"count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
