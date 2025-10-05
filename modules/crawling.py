#%%
from bs4 import BeautifulSoup
import requests

from typing import List





def extract_links(url: str, selector: str, tag: str = "a", attr: str = "href") -> List[str]:
    """
    주어진 URL에서 특정 selector 하위의 tag에서 attr 속성들을 추출
    
    Args:
        url (str): 크롤링할 페이지 URL
        selector (str): CSS selector (예: "div.company-news", "div.news-list")
        tag (str): 추출할 태그 이름 (기본값 "a")
        attr (str): 추출할 속성 (기본값 "href")
    
    Returns:
        List[str]: 추출된 속성값 리스트
    """
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.select(selector + f" {tag}")  # selector 하위의 tag 추출

    results = []
    for el in elements:
        value = el.get(attr)
        if value:
            results.append(value)

    # 중복 제거
    return list(set(results))



def get_contents(
    url: str,
    selector: str = 'sm-section-inner',
):
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')

    # sm-section-inner 클래스 div 찾기
    sections = soup.find_all('div', class_=selector)

    all_texts = []
    all_images = []

    for section in sections:
        # img 태그는 따로 보관
        for img in section.find_all('img'):
            img_info = {
                "src": img.get("src"),
                "alt": img.get("alt", "")  # alt 없으면 빈 문자열
            }
            all_images.append(img_info)
            img.decompose()  # ✅ 추출 후 제거 (텍스트 추출시 안 섞이게)

        # 남은 텍스트는 태그 포함해서 보관
        text_parts = section.decode_contents()
        all_texts.append(text_parts)

    text_with_tags = '\n'.join(all_texts)

    return {
        'html': text_with_tags,
        'images': all_images,
    }



if __name__ == '__main__':


    url = "https://www.smentertainment.com/newsroom/"
    company_news_links = extract_links(url, "div.company-news", tag="a", attr="href")

    # print(company_news_links)


    output = []

    for detail_url in company_news_links:
        data = get_contents(url)
        output.append(data)


    # news_list_links = extract_links(url, "div.news-list", tag="a", attr="href")

    # print(news_list_links)

    # url = 'https://www.smentertainment.com/newsroom/%ed%95%98%ec%b8%a0%ed%88%ac%ed%95%98%ec%b8%a0%ec%99%80-%ed%95%a8%ea%bb%98%ed%95%98%eb%8a%94-%ed%8a%b9%eb%b3%84%ed%95%9c-%ed%86%a0%ec%9a%94%ec%9d%bc-%ec%9d%b4%eb%b2%88-%ec%a3%bc-%ec%9d%8c/'
    # output = get_contents(url)
    # print(output)
