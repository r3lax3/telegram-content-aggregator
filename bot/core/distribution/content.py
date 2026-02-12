import re


URL_REGEX = re.compile(
    r'(?i)\b'
    r'(?:https?://|www\.|[a-z0-9-]+\.)'
    r'[a-z0-9.-]+'
    r'(?:/[^\s<>"{}|\\^`\[\]]*)?',
    re.IGNORECASE
)

POST_FOOTER = "\n\n<a href=\"{invite_link}\"><b>{channel_name} — новости</b></a>"


def have_source_link(text: str) -> bool:
    if not text:
        return False

    if URL_REGEX.search(text):
        return True

    if re.search(r'<a\s[^>]*href\s*=', text, re.IGNORECASE):
        return True

    if re.search(r'@\w{1,32}\b', text):
        return True

    if re.search(r'#\w{1,64}\b', text):
        return True

    return False


def delete_bottom_links(text: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()

    i = len(lines) - 1
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped:
            i -= 1
        elif stripped and have_source_link(stripped):
            i -= 1
        else:
            break

    clean_lines = lines[:i + 1]

    result = '\n'.join(clean_lines).rstrip()
    result = fix_unclosed_tags(result)

    return result


def fix_unclosed_tags(text: str) -> str:
    pattern = re.compile(r'<(/?)(b|i|u|s)\b[^>]*?>', re.IGNORECASE)
    stack = []
    for m in pattern.finditer(text):
        is_close = m.group(1) == '/'
        tag = m.group(2).lower()
        if not is_close:
            stack.append(tag)
        else:
            for i in range(len(stack)-1, -1, -1):
                if stack[i] == tag:
                    stack.pop(i)
                    break

    for tag in reversed(stack):
        text += f'</{tag}>'
    return text


def add_channel_footer(text: str, invite_link: str, channel_name: str) -> str:
    if not text.rstrip():
        return ""

    return text.rstrip() + POST_FOOTER.format(
        invite_link=invite_link,
        channel_name=channel_name
    )


def prepare_text(text: str, invite_link: str, channel_name: str) -> str:
    text = delete_bottom_links(text)
    text = add_channel_footer(text, invite_link, channel_name)

    return text
