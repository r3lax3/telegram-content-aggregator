import re


URL_REGEX = re.compile(
    r'(?i)\b'
    r'(?:https?://|www\.|[a-z0-9-]+\.)'
    r'[a-z0-9.-]+'
    r'(?:/[^\s<>"{}|\\^`\[\]]*)?',
    re.IGNORECASE
)

USERNAME_REGEX = re.compile(r'@\w{1,32}\b')
HASHTAG_REGEX = re.compile(r'#\w{1,64}\b')


def is_advertisement(text: str) -> bool:
    if not text:
        return False

    conditions = [
        URL_REGEX.search(text),
        USERNAME_REGEX.search(text),
        HASHTAG_REGEX.search(text)
    ]
    return any(conditions)
