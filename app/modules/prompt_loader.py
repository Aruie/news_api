import os

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def load_prompt(name: str) -> str:
    """
    지정된 프롬프트 템플릿 파일을 로드
    Args:
        name (str): 파일명 (확장자 제외)
    Returns:
        str: 프롬프트 문자열
    """
    path = os.path.join(PROMPT_DIR, f"{name}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

