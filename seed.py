import boto3
from datetime import datetime

# ✅ DynamoDB 클라이언트/리소스 초기화
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
client = boto3.client("dynamodb", region_name="us-east-1")


# ✅ 테이블이 존재하면 삭제
def delete_table_if_exists(table_name: str):
    try:
        client.describe_table(TableName=table_name)
        print(f"⚠️ Table '{table_name}' already exists. Deleting...")
        client.delete_table(TableName=table_name)
        waiter = client.get_waiter("table_not_exists")
        waiter.wait(TableName=table_name)
        print(f"🧹 Table '{table_name}' deleted.")
    except client.exceptions.ResourceNotFoundException:
        print(f"✅ Table '{table_name}' not found. (nothing to delete)")


# ✅ 테이블 생성
def create_tables():
    delete_table_if_exists("SourceMetaTable")
    delete_table_if_exists("ArticleTable")
    delete_table_if_exists("NewsTable")

    # --- 1️⃣ SourceMetaTable ---
    table_sources = dynamodb.create_table(
        TableName="SourceMetaTable",
        KeySchema=[{"AttributeName": "sourceId", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "sourceId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print("🆕 Created table: SourceMetaTable")

    # --- 2️⃣ ArticleTable ---
    table_articles = dynamodb.create_table(
        TableName="ArticleTable",
        KeySchema=[{"AttributeName": "articleId", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "articleId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print("🆕 Created table: ArticleTable")

    # --- 3️⃣ NewsTable ---
    table_news = dynamodb.create_table(
        TableName="NewsTable",
        KeySchema=[{"AttributeName": "articleId", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "articleId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    print("🆕 Created table: NewsTable")

    # --- 생성 완료 대기 ---
    print("⏳ Waiting for tables to become active...")
    table_sources.wait_until_exists()
    table_articles.wait_until_exists()
    table_news.wait_until_exists()
    print("✅ All tables are active!")


# ✅ 샘플 데이터 삽입
def insert_sample_data():
    sources_table = dynamodb.Table("SourceMetaTable")
    articles_table = dynamodb.Table("ArticleTable")
    news_table = dynamodb.Table("NewsTable")

    # --- 수집처 메타 ---
    source_item = {
        "sourceId": "ENT-0001",
        "srcName": "SM 뉴스룸",
        "srcDescription": "SM엔터테인먼트 공식 뉴스 게시판",
        "url": "https://www.smentertainment.com/newsroom/",
        "selectorContainer": "div.news-list",
        "selectorItem": "a",
        "category": "Entertainment",
    }

    # --- 원본 기사 ---
    article_item = {
        "articleId": "ENT-0001-251002-001",
        "sourceId": "ENT-0001",
        "url": "https://www.smentertainment.com/newsroom/view/12345",
        "title": "NCT NEW ALBUM 발표",
        "content": "SM엔터테인먼트는 오늘 NCT의 새 앨범 출시를 발표했다...",
        "imageUrl": "https://s3.ap-northeast-2.amazonaws.com/my-bucket/images/nct_album.jpg",
        "date": "2025-10-02",
        "category": "Entertainment",
    }

    # --- 생성된 뉴스 ---
    news_item = {
        "articleId": "060bf4c6",
        "category": "General",
        "title": "여기 뉴스 기사 형식으로 작성해 드렸습니다:",
        "author": "System",
        "pubDate": datetime.utcnow().isoformat(),
        "description": "AI가 자동으로 작성한 뉴스입니다.",
        "sourceArticleId": "ENT-0001-251002-001",
    }

    sources_table.put_item(Item=source_item)
    articles_table.put_item(Item=article_item)
    news_table.put_item(Item=news_item)
    print("✅ Sample data inserted successfully.")


# ✅ 실행 엔트리포인트
if __name__ == "__main__":
    create_tables()
    insert_sample_data()
    print("🎉 DynamoDB setup completed successfully!")
