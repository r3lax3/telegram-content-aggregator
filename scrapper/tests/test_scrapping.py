# tests/test_scrapping.py
import asyncio
import pytest
from pathlib import Path

from core.scrapper.browser import PlaywrightManager
from core.scrapper.service import ScrapperService
from core.scrapper.parser import parse_channel_posts


CHANNELS = [
    "abakan_smi",
    "angarsk_today",
    "arhangelkoroche",
    "astrakhan20",
    "ngs22ru_news",
    "belgorod1",
    "irk01",
    "kazan",
    "msk7days",
    "live_piter",
]

OUTPUT_FILE = Path("tests/scrapper_results.txt")


@pytest.mark.asyncio
async def test_scrapper_parses_channels():
    """
    Интеграционный тест: парсит 10 каналов, записывает результаты в файл.
    
    Требования:
    - файл tg_acc.session должен существовать (создать через scripts/create_tg_session.py)
    
    Запуск: pytest tests/test_scrapping.py -v -s
    """
    results: dict[str, list] = {}
    
    async with PlaywrightManager() as pw_manager:
        service = ScrapperService(pw_manager)
        
        print("\n" + "="*40)
        print("ГЕНЕРАЦИЯ COOKIES")
        print("="*40)
        await service._regenerate_cookies()
        print("Cookies успешно сгенерированы\n")
        
        for channel in CHANNELS:
            print(f"\nПарсинг @{channel}...")
            
            try:
                html = await service._fetch_channel_html(channel)
                posts = parse_channel_posts(html, channel)
                results[channel] = posts
                print(f"  OK: {len(posts)} постов")
                
            except Exception as e:
                print(f"  ОШИБКА: {e}")
                results[channel] = []
            
            await asyncio.sleep(5)
    
    _write_results(results)
    _print_stats(results)
    
    total = sum(len(posts) for posts in results.values())
    assert total > 0, "Не удалось спарсить ни одного поста"


def _write_results(results: dict[str, list]):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for channel, posts in results.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"@{channel} — {len(posts)} постов\n")
            f.write(f"{'='*60}\n\n")
            
            for post in posts[:10]:
                text_preview = post.text[:50].replace("\n", " ") if post.text else "(без текста)"
                f.write(f"[{post.id}] {text_preview}...\n")
                
                for media in post.medias:
                    f.write(f"       {media.type}: {media.url}\n")
                
                f.write("\n")
    
    print(f"\nРезультаты записаны в {OUTPUT_FILE}")


def _print_stats(results: dict[str, list]):
    print("\n" + "="*40)
    print("СТАТИСТИКА")
    print("="*40)
    
    for channel, posts in sorted(results.items(), key=lambda x: -len(x[1])):
        media_count = sum(len(p.medias) for p in posts)
        print(f"@{channel:20} | {len(posts):3} постов | {media_count:3} медиа")
    
    total_posts = sum(len(posts) for posts in results.values())
    total_media = sum(len(p.medias) for posts in results.values() for p in posts)
    
    print("-"*40)
    print(f"{'ИТОГО':21} | {total_posts:3} постов | {total_media:3} медиа")
