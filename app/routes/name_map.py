from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from app.modules.name_mapper import (
    load_name_map_text,
    append_name_entry,
    overwrite_name_map,
    delete_name_entry,
)

router = APIRouter(prefix="/name-map", tags=["Name Mapping"])

class NameEntry(BaseModel):
    korean: str
    english: str
    description: str = ""


@router.get("")
def get_all_lines():
    """전체 name_map.txt 원문 반환"""
    text = load_name_map_text()
    return {"content": text}


@router.post("")
def add_new_entry(entry: NameEntry):
    """새 항목 추가 (중복 허용)"""
    line = f"{entry.korean}|{entry.english}|{entry.description}"
    append_name_entry(line)
    return {"message": "추가 완료", "entry": line}


@router.put("")
def overwrite_whole_file(content: str = Body(..., embed=False)):
    """전체 파일 덮어쓰기"""
    if not content.strip():
        raise HTTPException(status_code=400, detail="내용이 비어 있습니다.")
    overwrite_name_map(content)
    return {"message": "파일 전체 덮어쓰기 완료"}



@router.delete("/{korean_name}")
def delete_entry(korean_name: str):
    """한글명 기준으로 해당 라인 삭제"""
    try:
        delete_name_entry(korean_name)
        return {"message": f"'{korean_name}' 관련 항목 삭제 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
