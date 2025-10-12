# app.py
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# 모듈 import
from app.modules.bedrock import call_bedrock_api
from app.modules.crawling import get_contents


from app.routes.news import router as news_router
from app.routes.source import router as source_router
from app.routes.articles import router as articles_router
from app.routes.scrap import router as scrap_router
from app.routes.name_map import router as name_router



app = FastAPI(title="My API Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],             
    allow_credentials=True,
    allow_methods=["*"],             
    allow_headers=["*"],             
)

app.include_router(news_router)
app.include_router(source_router)
app.include_router(articles_router)
app.include_router(scrap_router)
app.include_router(name_router)


# -------------------------------
# Request/Response 모델 정의
# -------------------------------

class BedrockRequest(BaseModel):
    prompt: str
    messages: Optional[str] = None
    model_name: str = "haiku-3.5"


class BedrockResponse(BaseModel):
    output: str
    raw: dict


class CrawlResponse(BaseModel):
    html: str
    images: List[dict]


# -------------------------------
# 엔드포인트 정의
# -------------------------------

@app.get("/")
def root():
    return {"message": "API is running!"}


@app.post("/bedrock", response_model=BedrockResponse)
def run_bedrock(req: BedrockRequest):
    """Bedrock 모델 호출"""
    result = call_bedrock_api(
        prompt=req.prompt,
        messages=req.messages or "",
        model_name=req.model_name,
    )

    # Claude 계열 응답 파싱
    try:
        output_text = result["content"][0]["text"]
    except Exception:
        output_text = str(result)

    return BedrockResponse(output=output_text, raw=result)


@app.get("/crawl", response_model=CrawlResponse)
def crawl_url(url: str = Query(..., description="크롤링할 URL"),
              selector: str = Query("sm-section-inner", description="div selector class")):
    """웹페이지에서 콘텐츠 추출"""
    contents = get_contents(url, selector)
    return CrawlResponse(**contents)


