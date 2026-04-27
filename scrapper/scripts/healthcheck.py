"""
Утилита проверки готовности проекта к запуску.

Запуск:
    cd scrapper && python scripts/healthcheck.py
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Корень проекта (на уровень выше папки scrapper)
SCRIPT_DIR = Path(__file__).parent
SCRAPPER_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SCRAPPER_DIR.parent

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg: str) -> str:
    return f"{GREEN}[OK]  {RESET} {msg}"


def fail(msg: str) -> str:
    return f"{RED}[FAIL]{RESET} {msg}"


def skip(msg: str) -> str:
    return f"{YELLOW}[SKIP]{RESET} {msg}"


def parse_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


passed = 0
total = 0


def check(result: bool, ok_msg: str, fail_msg: str) -> bool:
    global passed, total
    total += 1
    if result:
        passed += 1
        print(ok(ok_msg))
    else:
        print(fail(fail_msg))
    return result


def check_skip(msg: str):
    print(skip(msg))


# ─────────────────────────────────────────────────────────
# Проверка конфиг-файлов
# ─────────────────────────────────────────────────────────

def check_env_files() -> tuple[dict, dict]:
    bot_env_path = PROJECT_DIR / "bot.env"
    scrapper_env_path = PROJECT_DIR / "scrapper.env"

    if bot_env_path.exists():
        check(True, "bot.env найден", "")
    else:
        check_skip(f"bot.env не найден ({bot_env_path}) — используются переменные окружения")

    if scrapper_env_path.exists():
        check(True, "scrapper.env найден", "")
    else:
        check_skip(f"scrapper.env не найден ({scrapper_env_path}) — используются переменные окружения")

    file_bot = parse_env_file(bot_env_path)
    file_scrapper = parse_env_file(scrapper_env_path)

    merged_bot = {
        **file_bot,
        **{k: v for k, v in os.environ.items() if k in ["BOT_TOKEN", "DATABASE_URL", "RABBITMQ_URL", "SCRAPPER_API_URL"]},
    }
    merged_scrapper = {
        **file_scrapper,
        **{k: v for k, v in os.environ.items() if k in ["DATABASE_URL", "RABBITMQ_URL"]},
    }

    return merged_bot, merged_scrapper


# ─────────────────────────────────────────────────────────
# Проверка переменных окружения
# ─────────────────────────────────────────────────────────

def check_env_vars(bot_env: dict, scrapper_env: dict):
    bot_required = ["BOT_TOKEN", "DATABASE_URL", "RABBITMQ_URL", "SCRAPPER_API_URL"]
    scrapper_required = ["DATABASE_URL", "RABBITMQ_URL"]

    bot_missing = [k for k in bot_required if not bot_env.get(k)]
    scrapper_missing = [k for k in scrapper_required if not scrapper_env.get(k)]

    check(
        not bot_missing,
        "Все обязательные переменные бота заданы",
        f"В bot.env не заданы: {', '.join(bot_missing)}",
    )
    check(
        not scrapper_missing,
        "Все обязательные переменные скрапера заданы",
        f"В scrapper.env не заданы: {', '.join(scrapper_missing)}",
    )


# ─────────────────────────────────────────────────────────
# Проверка Telegram Bot токена
# ─────────────────────────────────────────────────────────

def check_bot_token(bot_env: dict):
    token = bot_env.get("BOT_TOKEN")
    if not token:
        check(False, "", "BOT_TOKEN не задан, пропускаем проверку токена")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("ok"):
            bot = data["result"]
            check(True, f"Telegram Bot: @{bot.get('username')} (id={bot.get('id')})", "")
        else:
            check(False, "", f"Токен невалиден: {data.get('description')}")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        check(False, "", f"Токен невалиден: {body.get('description', e)}")
    except Exception as e:
        check(False, "", f"Ошибка проверки токена: {e}")


# ─────────────────────────────────────────────────────────
# Проверка t.me/s/ доступности
# ─────────────────────────────────────────────────────────

def check_telegram_preview():
    url = "https://t.me/s/durov"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        if 'tgme_widget_message' in html:
            check(True, f"t.me/s доступен (получены сообщения с {url})", "")
        else:
            check(False, "", f"t.me/s ответил, но сообщений в HTML не нашлось")
    except Exception as e:
        check(False, "", f"t.me/s недоступен: {e}")


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

async def main():
    print(f"\n{BOLD}=== Проверка готовности проекта ==={RESET}\n")

    bot_env, scrapper_env = check_env_files()
    print()

    check_env_vars(bot_env, scrapper_env)
    print()

    check_bot_token(bot_env)
    print()

    check_telegram_preview()
    print()

    color = GREEN if passed == total else RED
    print(f"{BOLD}{color}=== Итог: {passed}/{total} проверок прошло ==={RESET}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
