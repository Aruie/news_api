from bs4 import BeautifulSoup
import requests
from typing import List, Dict
from urllib.parse import urlparse, urljoin, urlunparse

def clean_html(soup: BeautifulSoup) -> str:
    """
    불필요한 속성(style, class, id 등) 제거 후 HTML 문자열로 반환
    """
    # 1️⃣ 불필요한 태그 자체 제거
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    # 2️⃣ 각 태그의 불필요한 속성 제거
    for tag in soup.find_all(True):  # True → 모든 태그
        allowed_attrs = {"href", "src", "alt"}  # 유지할 속성
        attrs = dict(tag.attrs)
        for attr in list(attrs.keys()):
            if attr not in allowed_attrs:
                del tag.attrs[attr]

    # 3️⃣ 정돈된 HTML 반환
    return str(soup)

def normalize_url(base_url: str, link: str) -> str:
    """
    상대경로 → 절대경로 변환 후, 중복된 path 구간 정리
    예: /ko/news/notice/ko/news/notice/5858 → /ko/news/notice/5858
    """
    # 1️⃣ 절대 URL로 변환
    full_url = urljoin(base_url, link)

    # 2️⃣ URL 파싱
    parsed = urlparse(full_url)
    path_parts = [p for p in parsed.path.split('/') if p]

    # 3️⃣ 중복된 연속 패턴 제거
    cleaned = []
    for part in path_parts:
        # 같은 구간이 연속으로 반복되면 하나만 유지
        if len(cleaned) >= 2 and cleaned[-2:] == [part, part]:
            continue
        cleaned.append(part)

    # 4️⃣ 중복 구간 (ex. /ko/news/notice/ko/news/notice/5858)
    #    같은 패턴 반복시 앞부분만 유지
    joined = '/'.join(cleaned)
    while True:
        half = joined[: len(joined)//2]
        if half and joined.startswith(half + '/' + half):
            joined = joined[len(half)+1:]
        else:
            break

    new_path = '/' + joined

    # 5️⃣ 다시 조립
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        new_path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))
    return normalized


def extract_links(url: str, selector: str, tag: str = "a", attr: str = "href") -> List[str]:
    """
    주어진 URL에서 특정 selector 하위의 tag에서 attr 속성들을 추출
    
    Args:
        url (str): 크롤링할 페이지 URL
        selector (str): CSS selector (예: "div.company-news", "div.news-list")
        tag (str): 추출할 태그 이름 (기본값 "a")
        attr (str): 추출할 속성 (기본값 "href")
    
    Returns:
        List[str]: 추출된 (정규화된) URL 리스트
    """
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.select(selector + f" {tag}")
    if not elements:
        raise ValueError(f"❌ extract_links: '{selector} {tag}' selector로 매칭된 요소가 없습니다. ({url})")

    results = []
    for el in elements:
        raw_link = el.get(attr)
        if not raw_link:
            continue
        normalized = normalize_url(url, raw_link)
        results.append(normalized)

    if not results:
        raise ValueError(f"❌ extract_links: '{attr}' 속성이 존재하지 않습니다. ({url})")

    return list(set(results))  # ✅ 중복 제거


def get_contents(url: str, selector: str) -> Dict[str, List[Dict[str, str]]]:
    """
    지정된 CSS selector로 본문(html + 이미지) 추출 (스타일 제거 버전)
    """
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    sections = soup.select(selector)
    if not sections:
        raise ValueError(f"❌ get_contents: selector '{selector}' 로 매칭된 요소가 없습니다. ({url})")

    all_texts, all_images = [], []

    for section in sections:
        # 이미지 추출
        for img in section.find_all("img"):
            img_info = {"src": img.get("src"), "alt": img.get("alt", "")}
            all_images.append(img_info)

        # ✅ 스타일/클래스 등 속성 제거
        clean_section_html = clean_html(section)

        if clean_section_html.strip():
            all_texts.append(clean_section_html)

    text_with_tags = "\n".join(all_texts).strip()
    if not text_with_tags:
        raise ValueError(f"❌ get_contents: selector '{selector}' 내부에서 본문 텍스트를 추출하지 못했습니다. ({url})")

    return {"html": text_with_tags, "images": all_images}