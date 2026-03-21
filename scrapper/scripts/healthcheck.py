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
from urllib.parse import urlparse

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

def check_env_files(bot_env: dict, scrapper_env: dict) -> tuple[dict, dict]:
    bot_env_path = PROJECT_DIR / "bot.env"
    scrapper_env_path = PROJECT_DIR / "scrapper.env"

    check(bot_env_path.exists(), "bot.env найден", f"bot.env не найден (ожидается: {bot_env_path})")
    check(scrapper_env_path.exists(), "scrapper.env найден", f"scrapper.env не найден (ожидается: {scrapper_env_path})")

    return parse_env_file(bot_env_path), parse_env_file(scrapper_env_path)


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
# Проверка прокси
# ─────────────────────────────────────────────────────────

def check_proxy(scrapper_env: dict):
    proxy_server = scrapper_env.get("PROXY_SERVER")
    if not proxy_server:
        check_skip("PROXY_SERVER не задан, прокси не используется")
        return

    proxy_user = scrapper_env.get("PROXY_USERNAME", "")
    proxy_pass = scrapper_env.get("PROXY_PASSWORD", "")

    parsed = urlparse(proxy_server)
    if proxy_user:
        proxy_url = f"{parsed.scheme}://{proxy_user}:{proxy_pass}@{parsed.netloc}"
    else:
        proxy_url = proxy_server

    try:
        proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        if proxy_user:
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, proxy_server, proxy_user, proxy_pass)
            auth_handler = urllib.request.ProxyBasicAuthHandler(password_mgr)
            opener = urllib.request.build_opener(proxy_handler, auth_handler)
        else:
            opener = urllib.request.build_opener(proxy_handler)

        req = urllib.request.Request(
            "https://api.ipify.org?format=json",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read())
        check(True, f"Прокси работает (IP: {data.get('ip')})", "")
    except Exception as e:
        check(False, "", f"Прокси недоступен ({proxy_server}): {e}")


# ─────────────────────────────────────────────────────────
# Проверка файлов сессии и кукисов
# ─────────────────────────────────────────────────────────

def check_session_and_cookies():
    session_path = SCRAPPER_DIR / "tg_acc.session"
    cookies_path = SCRAPPER_DIR / "cookies.json"

    check(
        session_path.exists(),
        f"tg_acc.session найден",
        f"tg_acc.session не найден — создайте через: python scripts/create_tg_session.py",
    )

    if cookies_path.exists():
        try:
            data = json.loads(cookies_path.read_text(encoding="utf-8"))
            check(isinstance(data, list), "cookies.json найден и валиден", "cookies.json не является списком")
        except json.JSONDecodeError as e:
            check(False, "", f"cookies.json невалидный JSON: {e}")
    else:
        check(False, "", "cookies.json не найден")


# ─────────────────────────────────────────────────────────
# Проверка tgstat.ru через Playwright
# ─────────────────────────────────────────────────────────

async def check_tgstat(scrapper_env: dict):
    global passed, total
    total += 1

    try:
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        print(fail("playwright не установлен"))
        return

    proxy_server = scrapper_env.get("PROXY_SERVER")
    proxy_user = scrapper_env.get("PROXY_USERNAME")
    proxy_pass = scrapper_env.get("PROXY_PASSWORD")

    proxy_config = None
    if proxy_server:
        proxy_config = {"server": proxy_server}
        if proxy_user:
            proxy_config["username"] = proxy_user
            proxy_config["password"] = proxy_pass

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36"
                ),
                proxy=proxy_config,
            )
            page = await context.new_page()

            try:
                response = await page.goto(
                    "https://tgstat.ru/channel/@durov",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
            except PlaywrightTimeoutError:
                print(fail("tgstat.ru: таймаут загрузки (30с) — возможно, нет прокси или заблокирован доступ"))
                await browser.close()
                return

            title = await page.title()

            if "just a moment" in title.lower() or "checking your browser" in title.lower():
                print(fail(f"tgstat.ru: Cloudflare challenge — нужны валидные куки или другой прокси"))
                await browser.close()
                return

            if response and response.status == 429:
                print(fail("tgstat.ru: 429 Too Many Requests — превышен лимит запросов"))
                await browser.close()
                return

            if response and response.status != 200:
                print(fail(f"tgstat.ru: HTTP {response.status}"))
                await browser.close()
                return

            try:
                await page.wait_for_selector("div.posts-list.lm-list-container", timeout=10_000)
                posts = await page.query_selector_all("div.post-container, .post-row, [data-post-id]")
                count = len(posts)
                if count > 0:
                    passed += 1
                    print(ok(f"tgstat.ru: {count} постов найдено для @durov"))
                else:
                    print(fail("tgstat.ru: контейнер постов найден, но постов 0 — возможно, изменилась структура страницы"))
            except PlaywrightTimeoutError:
                print(fail("tgstat.ru: страница загрузилась, но контейнер постов не появился — возможно Cloudflare или изменилась структура"))

            await browser.close()

    except Exception as e:
        print(fail(f"tgstat.ru: ошибка при запуске Playwright — {e}"))


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

async def main():
    print(f"\n{BOLD}=== Проверка готовности проекта ==={RESET}\n")

    bot_env, scrapper_env = check_env_files({}, {})
    print()

    check_env_vars(bot_env, scrapper_env)
    print()

    check_bot_token(bot_env)
    print()

    check_proxy(scrapper_env)
    print()

    check_session_and_cookies()
    print()

    await check_tgstat(scrapper_env)
    print()

    color = GREEN if passed == total else RED
    print(f"{BOLD}{color}=== Итог: {passed}/{total} проверок прошло ==={RESET}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
