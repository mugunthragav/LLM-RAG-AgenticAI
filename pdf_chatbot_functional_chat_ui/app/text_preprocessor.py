import re

def preprocess_text(text: str) -> str:
    # Basic cleaning: remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', text)
    return cleaned.strip()
