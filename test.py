import asyncio

import httpx

import algorithmic.data_source.sec as sec


async def main():
    headers = sec.build_http_headers()

    async with httpx.AsyncClient(headers=headers) as client:
        result = await sec.lookup_cik(client, "Nvda")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
