import os

NAME_MAP_FILE = os.path.join(os.path.dirname(__file__), "prompts", "name_map.txt")

def load_name_map_text() -> str:
    """
    name_map.txt 파일의 원문을 그대로 불러옴.
    (한글명|영문명|간단설명)
    """
    if not os.path.exists(NAME_MAP_FILE):
        return ""
    with open(NAME_MAP_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def append_name_entry(entry_line: str):
    """
    새 항목(한글명|영문명|간단설명)을 파일 맨 아래에 추가
    """
    with open(NAME_MAP_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + entry_line.strip())


def overwrite_name_map(new_text: str):
    """
    전체 내용을 덮어쓰기 (파일 교체)
    """
    with open(NAME_MAP_FILE, "w", encoding="utf-8") as f:
        f.write(new_text.strip())


def delete_name_entry(korean_name: str):
    """
    특정 한글명으로 시작하는 라인 삭제
    (한글명|... 형태에서 첫 번째 구분자 전까지 일치하는 라인을 제거)
    """
    if not os.path.exists(NAME_MAP_FILE):
        raise FileNotFoundError("name_map.txt not found")

    with open(NAME_MAP_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.split("|", 1)[0] == korean_name:
            new_lines.append(stripped)

    with open(NAME_MAP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
