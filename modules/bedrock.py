# modules/bedrock.py
import boto3
import json
import re

# ✅ Bedrock 클라이언트
client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

model_ids = {
    'haiku-3.5': 'arn:aws:bedrock:us-east-1:678005315499:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0'
}


def call_bedrock_api(prompt: str, model_name: str = 'haiku-3.5'):
    """
    Bedrock Claude 3.5 API 호출
    """
    response = client.invoke_model(
        modelId=model_ids[model_name],
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7,
        }),
        contentType="application/json",
        accept="application/json"
    )
    result = json.loads(response["body"].read())
    return result


def parse_bedrock_output(text: str):
    """
    Claude 출력에서 <Title> / <Article> 태그 추출
    """
    title_match = re.search(r"<Title>(.*?)</Title>", text, re.DOTALL)
    article_match = re.search(r"<Article>(.*?)</Article>", text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    article = article_match.group(1).strip() if article_match else ""
    return title, article


# ✅ 테스트 실행용
if __name__ == '__main__':
    test_prompt = """
    다음 텍스트를 바탕으로 뉴스 형식으로 요약하고,
    <Title> / <Article> 구조로 작성하세요.

    내용: NCT가 새로운 앨범을 발표하며 팬들의 기대를 모으고 있다.
    """
    result = call_bedrock_api(test_prompt)
    text = result["content"][0]["text"]
    title, article = parse_bedrock_output(text)
    print("📰 제목:", title)
    print("📄 본문:", article)
