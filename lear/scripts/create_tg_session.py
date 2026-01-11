from telethon import TelegramClient


# Remember to use your own values from my.telegram.org!
api_id = 37443963
api_hash = 'f5092f2f7523d78fb82fbe6ff126bb60'

client = TelegramClient('tg_acc', api_id, api_hash)


async def main():
    me = await client.get_me()

    print(f"Me is @{me.username}")


with client:
    client.loop.run_until_complete(main())
