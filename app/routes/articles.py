from fastapi import APIRouter, HTTPException
import boto3
import uuid
import re
from app.modules.bedrock import call_bedrock_api, parse_bedrock_output
from app.modules.prompt_loader import load_prompt  
from app.modules.name_mapper import load_name_map_text

from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/articles", tags=["Articles"])

# ✅ AWS 리소스
region = "us-east-1"
dynamodb = boto3.resource("dynamodb", region_name=region)
s3 = boto3.client("s3", region_name=region)

article_table = dynamodb.Table("ArticleTable")
news_table = dynamodb.Table("NewsTable")
TARGET_BUCKET = "sayart-news-thumbnails"


@router.post("/generate-news/{article_id}")
def generate_news_from_article(article_id: str):
    """기사 기반으로 뉴스 생성"""
    try:
        res = article_table.get_item(Key={"articleId": article_id})
        if "Item" not in res:
            raise HTTPException(status_code=404, detail="Article not found")
        article = res["Item"]

        category = article.get("category")
        if not category:
            raise HTTPException(status_code=400, detail="Missing category info")

        raw_image_url = article.get("imageUrl", "")
        if raw_image_url and raw_image_url.strip().startswith("data:image"):
            image_url = ""   # base64 데이터일 경우 무시
        else:
            image_url = raw_image_url

        origin_url = article.get("articleUrl")

        # 프롬프트 불러오기
        try:
            template = load_prompt("generate_news") 
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prompt load failed: {e}")


        name_map_text = load_name_map_text()
        # ✅ 템플릿 변수 치환
        prompt = (
            template
            .replace("{{content}}", article.get("content", ""))
            .replace("{{name_map}}", name_map_text)
        )

        # ✅ Bedrock 호출
        result = call_bedrock_api(prompt=prompt, model_name="haiku-3.5")
        text = result["content"][0]["text"] if "content" in result else str(result)
        title, description = parse_bedrock_output(text)
        
        

        if not title or not description:
            raise HTTPException(status_code=500, detail="Bedrock output parsing failed")
        
        description = re.sub(r'\n{2,}', '</p><p>', description.strip())
        description = f"<p>{description}</p>"


        # ✅ 새 뉴스 생성
        new_id = str(uuid.uuid4().hex[:10])
        now = datetime.now(timezone.utc).isoformat()

        news_table.put_item(
            Item={
                "articleId": new_id,
                "title": title,
                "description": description,
                "sourceArticleId": article_id,
                "category": category,
                "pubDate": now,
                "author": "System",
                "imageUrl": image_url,
                "originUrl": origin_url,
            }
        )

        # ✅ ArticleTable에 generatedNewsId 업데이트
        article_table.update_item(
            Key={"articleId": article_id},
            UpdateExpression="SET generatedNewsId = :nid, generateFlag = :f",
            ExpressionAttributeValues={":nid": new_id, ":f": 1},
        )

        return {
            "message": "Generated successfully",
            "id": new_id,
            "title": title,
            "description": description,
            "category": category,
            "imageUrl": image_url,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch")
def generate_all_unprocessed_articles():
    """
    아직 뉴스가 생성되지 않은 기사들(generateFlag=0)을 모두 생성
    """
    try:
        # 1️⃣ generateFlag == 0 인 기사 목록 조회
        res = article_table.scan(
            FilterExpression="attribute_not_exists(generateFlag) OR generateFlag = :flag",
            ExpressionAttributeValues={":flag": 0}
        )
        articles = res.get("Items", [])
        if not articles:
            return {"message": "생성할 신규 기사 없음", "count": 0}

        total_success = 0
        total_fail = 0
        results = []

        for article in articles:
            article_id = article["articleId"]

            try:
                # 기존 단일 생성 로직 재사용
                sub_res = generate_news_from_article(article_id)

                # 성공 시 플래그 1로 업데이트
                article_table.update_item(
                    Key={"articleId": article_id},
                    UpdateExpression="SET generateFlag = :f, generateError = :e",
                    ExpressionAttributeValues={
                        ":f": 1,
                        ":e": "SUCCESS"
                    }
                )

                total_success += 1
                results.append({"articleId": article_id, "status": "success"})

            except Exception as e:
                # 실패 시 플래그 2 및 오류내용 기록
                article_table.update_item(
                    Key={"articleId": article_id},
                    UpdateExpression="SET generateFlag = :f, generateError = :e",
                    ExpressionAttributeValues={
                        ":f": 2,
                        ":e": str(e)
                    }
                )

                total_fail += 1
                results.append({"articleId": article_id, "status": f"failed: {e}"})

        return {
            "message": "Batch generation completed",
            "totalSuccess": total_success,
            "totalFail": total_fail,
            "processed": len(articles),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rss/generated")
def generate_and_upload_rss_to_s3():
    """
    오늘 생성된 뉴스 기반 RSS XML 생성 → S3 업로드 (퍼블릭)
    
    (xml.etree.ElementTree → xml.dom.minidom 기반으로 교체하여 진짜 CDATA 적용)
    """
    try:
        from xml.dom.minidom import Document

        KST = timezone(timedelta(hours=9))
        now_kst = datetime.now(KST)
        today_kst_str = now_kst.strftime("%Y-%m-%d")

        # 1️⃣ DynamoDB 뉴스 스캔
        res = news_table.scan()
        items = res.get("Items", [])

        # 2️⃣ 오늘 생성된 뉴스만 필터링
        recent_items = []
        for item in items:
            pub_date_str = item.get("pubDate", "")
            if not pub_date_str:
                continue
            try:
                pub_dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")).astimezone(KST)
                if pub_dt.strftime("%Y-%m-%d") == today_kst_str:
                    recent_items.append(item)
            except Exception:
                continue

        # 3️⃣ 최신순 정렬 + 최대 100개
        recent_items.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
        recent_items = recent_items[:100]

        # 4️⃣ DOM 기반 RSS XML 생성
        doc = Document()

        rss = doc.createElement("rss")
        rss.setAttribute("xmlns:atom", "http://www.w3.org/2005/Atom")
        rss.setAttribute("xmlns:art", "http://artnews.local/rss")
        rss.setAttribute("version", "2.0")
        doc.appendChild(rss)
        # script = doc.createElement("script")
        # rss.appendChild(script)

        channel = doc.createElement("channel")
        rss.appendChild(channel)

        def add_text(tag, text):
            el = doc.createElement(tag)
            el.appendChild(doc.createTextNode(text))
            channel.appendChild(el)
            return el

        add_text("title", "ArtNews Recent Articles")
        add_text("link", "http://cc.xxq.me/art_news/rss.xml")
        add_text("description", "오늘 생성된 아트 기사 목록")
        add_text("language", "ko")
        
        pub_str = now_kst.strftime("%a, %d %b %Y %H:%M:%S +0900")
        add_text("pubDate", pub_str)
        add_text("lastBuildDate", pub_str)

        atom_link = doc.createElement("atom:link")
        atom_link.setAttribute("href", "http://cc.xxq.me/art_news/rss.xml")
        atom_link.setAttribute("rel", "self")
        atom_link.setAttribute("type", "application/rss+xml")
        channel.appendChild(atom_link)

        byline = '''\n\nSayArt / Sayart Teams'''

        # 5️⃣ 아이템 루프
        for item in recent_items:
            item_el = doc.createElement("item")
            channel.appendChild(item_el)

            # 진짜 CDATA 블록 생성
            def add_cdata(tag, text):
                el = doc.createElement(tag)
                el.appendChild(doc.createCDATASection(text))
                item_el.appendChild(el)

            add_cdata("title", item.get("title", "Untitled"))
            link_el = doc.createElement("link")
            link_el.appendChild(doc.createTextNode(item.get("originUrl", "")))
            item_el.appendChild(link_el)
            add_cdata("description", item.get("description", "") + byline)
            add_cdata("category", item.get("category", "general"))

            # articleId (namespace 포함)
            # TODO: 수정필요 임시 하드코드 ( 어떻게 변할지 몰라서 )
            art_id = doc.createElement("art:articleId")
            # art_id.appendChild(doc.createTextNode(str(item.get("articleId", ""))))
            art_id.appendChild(doc.createTextNode(str(182012122)))
            item_el.appendChild(art_id)

            guid_el = doc.createElement("guid")
            guid_el.setAttribute("isPermaLink", "false")
            guid_el.appendChild(doc.createTextNode(item.get("articleId", "")))
            item_el.appendChild(guid_el)
            

            # imageUrl (첫 번째 이미지만)
            if item.get("imageUrl"):
                img_el = doc.createElement("imageUrl")
                img_el.appendChild(doc.createTextNode(item["imageUrl"]))
                item_el.appendChild(img_el)

            # pubDate (RFC 형식 변환)
            pub_dt = datetime.fromisoformat(
                item.get("pubDate", now_kst.isoformat())
            ).astimezone(KST)
            pub_date_str = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
            pub_el = doc.createElement("pubDate")
            pub_el.appendChild(doc.createTextNode(pub_date_str))
            item_el.appendChild(pub_el)

        # 6️⃣ XML 문자열 직렬화 (UTF-8)
        xml_bytes = doc.toprettyxml(indent="  ", encoding="utf-8")
        
        # BOM 추가
        BOM = b'\xef\xbb\xbf'
        xml_bytes = BOM + xml_bytes

        # 7️⃣ S3 업로드 (퍼블릭)
        file_name = f"rss/ArtNews_{today_kst_str}.xml"
        s3.put_object(
            Bucket=TARGET_BUCKET,
            Key=file_name,
            Body=xml_bytes,
            ContentType="application/rss+xml; charset=utf-8",
        )

        public_url = f"https://{TARGET_BUCKET}.s3.amazonaws.com/{file_name}"

        # ✅ 반환: RSS 업로드 정보만
        return {
            "message": "RSS generated and uploaded successfully",
            "itemCount": len(recent_items),
            "rssFile": file_name,
            "rssUrl": public_url,
            "generatedAt": pub_str,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
