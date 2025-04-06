import asyncio

import httpx

import algorithmic.data_source.sec as sec
from algorithmic.common.date_time import last_n_years


async def main():
    headers = sec.build_http_headers()

    async with httpx.AsyncClient(headers=headers) as client:
        cik = (await sec.lookup_cik(client, "Nvidia"))[0].cik
        filings = await sec.search_filings(
            client=client,
            ciks=[cik],
            form_types=[sec.FormType.F_10_K],
            date_range=last_n_years(1)
        )

        filing_id = filings.entries[0].id
        data = await sec.download_filing(client, filing_id)

        print(data)


if __name__ == "__main__":
    asyncio.run(main())
