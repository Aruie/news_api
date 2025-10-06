from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3
from boto3.dynamodb.conditions import Attr
import uuid

router = APIRouter(prefix="/sources", tags=["Sources"])

# DynamoDB
region = "us-east-1"
dynamodb = boto3.resource("dynamodb", region_name=region)
source_table = dynamodb.Table("SourceMetaTable")
article_table = dynamodb.Table("ArticleTable")


# -------------------------------
# ✅ Pydantic 모델
# -------------------------------
class SourceBase(BaseModel):
    srcName: str
    srcDescription: str
    sourceUrl: str
    selectorContainer: str
    selectorItem: str
    contentSelector: str  # ✅ 추가됨
    category: str


class SourceUpdate(SourceBase):
    pass


# -------------------------------
# ✅ API 구현
# -------------------------------

@router.get("")
def get_all_sources():
    """모든 수집처 목록 조회"""
    try:
        res = source_table.scan()
        return {"count": len(res["Items"]), "items": res["Items"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
def get_source(source_id: str):
    """단일 수집처 조회"""
    try:
        res = source_table.get_item(Key={"sourceId": source_id})
        if "Item" not in res:
            raise HTTPException(status_code=404, detail="Source not found")
        return res["Item"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_source(src: SourceBase):
    """새로운 수집처 추가"""
    try:
        source_id = f"SRC-{uuid.uuid4().hex[:8]}"

        item = {
            "sourceId": source_id,
            "srcName": src.srcName,
            "srcDescription": src.srcDescription,
            "sourceUrl": src.sourceUrl,
            "selectorContainer": src.selectorContainer,
            "selectorItem": src.selectorItem,
            "contentSelector": src.contentSelector,  # ✅ 추가됨
            "category": src.category,
        }

        source_table.put_item(Item=item)
        return {"message": "Created successfully", "sourceId": source_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{source_id}")
def update_source(source_id: str, data: SourceUpdate):
    """기존 수집처 정보 수정"""
    try:
        update_expr = """
        SET srcName=:n,
            srcDescription=:d,
            sourceUrl=:u,
            selectorContainer=:c,
            selectorItem=:i,
            contentSelector=:s,
            category=:g
        """

        values = {
            ":n": data.srcName,
            ":d": data.srcDescription,
            ":u": data.sourceUrl,
            ":c": data.selectorContainer,
            ":i": data.selectorItem,
            ":s": data.contentSelector,  # ✅ 추가됨
            ":g": data.category,
        }

        source_table.update_item(
            Key={"sourceId": source_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=values,
        )

        return {"message": "Updated successfully", "sourceId": source_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source_id}")
def delete_source(source_id: str):
    """수집처 삭제"""
    try:
        source_table.delete_item(Key={"sourceId": source_id})
        return {"message": "Deleted successfully", "sourceId": source_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}/articles")
def get_articles_by_source(source_id: str):
    """특정 수집처의 기사 목록 조회"""
    try:
        res = article_table.scan(FilterExpression=Attr("sourceId").eq(source_id))
        items = res.get("Items", [])
        return {"count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
