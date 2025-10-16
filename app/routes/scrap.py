from fastapi import APIRouter, HTTPException
from datetime import datetime
import boto3
import uuid
import traceback
from app.modules.crawling import extract_links, get_contents

router = APIRouter(prefix="/scrap", tags=["Scraper"])

# DynamoDB
region = "us-east-1"
dynamodb = boto3.resource("dynamodb", region_name=region)
source_table = dynamodb.Table("SourceMetaTable")
article_table = dynamodb.Table("ArticleTable")
lock_table = dynamodb.Table("ScrapLockTable")  # ✅ 락용 테이블 추가 (PK: "scrap-lock")


@router.post("/run")
def run_scraper():
    """
    ✅ 실시간 모니터링형 자동 수집기 (with DynamoDB Lock)
    - SourceMetaTable 기준으로 각 수집처 1회 스캔
    - 목록 selector / 본문 selector 둘 다 테이블에서 지정
    - 이미 등록된 URL은 제외
    - 신규 기사만 ArticleTable에 저장
    - 페이징 없음
    - 중복 실행 방지 (DynamoDB Lock)
    """

    # ✅ 1. 실행 중인지 확인
    try:
        lock_item = lock_table.get_item(Key={"PK": "scrap-lock"}).get("Item")
        if lock_item and lock_item.get("isRunning"):
            raise HTTPException(status_code=409, detail="Scraper already running")

        # ✅ 2. 락 설정
        lock_table.put_item(
            Item={
                "PK": "scrap-lock",
                "isRunning": True,
                "startedAt": datetime.utcnow().isoformat(),
            }
        )

        print("🚀 수집기 실행 시작")

        # ✅ 3. 실제 수집 로직
        res = source_table.scan()
        sources = res.get("Items", [])
        if not sources:
            raise HTTPException(status_code=404, detail="No sources found")

        total_new = 0
        total_skipped = 0
        total_failed = 0
        result_summary = []

        for src in sources:
            src_id = src["sourceId"]
            src_name = src["srcName"]
            base_url = src["sourceUrl"]
            selector_container = src.get("selectorContainer")
            selector_item = src.get("selectorItem", "a")
            selector_content = src.get("contentSelector")
            category = src.get("category", "General")

            print(f"🕷️ {src_name} ({src_id}) → {base_url}")

            try:
                links = extract_links(base_url, selector_container, selector_item)
            except Exception as e:
                print(f"⚠️ [{src_name}] 링크 추출 실패: {e}")
                total_failed += 1
                continue

            new_count = 0
            skip_count = 0
            fail_count = 0

            for link in links:
                # URL 정규화
                if link.startswith("/"):
                    full_url = base_url.rstrip("/") + link
                elif link.startswith("http"):
                    full_url = link
                else:
                    full_url = f"{base_url.rstrip('/')}/{link}"

                # 중복 확인
                exists = article_table.scan(
                    FilterExpression="articleUrl = :u",
                    ExpressionAttributeValues={":u": full_url}
                )
                if exists.get("Items"):
                    skip_count += 1
                    continue

                try:
                    # ✅ 본문 selector를 동적으로 전달
                    data = get_contents(full_url, selector_content)
                    html = data.get("html", "")
                    imgs = data.get("images", [])
                    image_url = imgs[0]["src"] if imgs else None

                    article_id = f"{src_id}-{uuid.uuid4().hex[:10]}"

                    article_table.put_item(
                        Item={
                            "articleId": article_id,
                            "sourceId": src_id,
                            "articleUrl": full_url,
                            "content": html,
                            "imageUrl": image_url,
                            "date": datetime.utcnow().isoformat(),
                            "category": category,
                            "contentSelector": selector_content,
                        }
                    )

                    new_count += 1
                    total_new += 1

                except Exception as e:
                    print(f"⚠️ [{src_name}] {full_url} 수집 실패: {e}")
                    fail_count += 1
                    total_failed += 1

            result_summary.append({
                "sourceId": src_id,
                "sourceName": src_name,
                "checkedLinks": len(links),
                "newArticles": new_count,
                "skipped": skip_count,
                "failed": fail_count,
            })
            total_skipped += skip_count

        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "totalNew": total_new,
            "totalSkipped": total_skipped,
            "totalFailed": total_failed,
            "summary": result_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # ✅ 4. 락 해제 (예외 발생 여부와 상관없이)
        try:
            lock_table.put_item(
                Item={
                    "PK": "scrap-lock",
                    "isRunning": False,
                    "finishedAt": datetime.utcnow().isoformat(),
                }
            )
            print("✅ 락 해제 완료")
        except Exception as unlock_err:
            print(f"⚠️ 락 해제 실패: {unlock_err}")
