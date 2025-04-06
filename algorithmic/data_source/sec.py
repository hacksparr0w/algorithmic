from typing import Optional

import lxml.html

from httpx import AsyncClient
from pydantic import BaseModel

from ..common.http import DEFAULT_USER_AGENT


SEC_URL = "https://www.sec.gov"


def _build_url(path: str) -> str:
    return SEC_URL + path


def build_http_headers(user_agent: Optional[str] = None) -> dict[str, str]:
    return {
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Gpc": "1",
        "User-Agent": user_agent or DEFAULT_USER_AGENT
    }


class CompanySearchResultEntry(BaseModel):
    cik: int
    name: str


class CompanyTickerEntry(BaseModel):
    cik: int
    name: str
    ticker: str
    exchange: Optional[str]


def _validate_company_ticker_entry(entry: list[str]) -> CompanyTickerEntry:
    cik, name, ticker, exchange = entry

    return CompanyTickerEntry(
        cik=cik,
        name=name,
        ticker=ticker,
        exchange=exchange
    )


def _validate_company_ticker_entries(data: dict) -> list[CompanyTickerEntry]:
    entries = data["data"]

    return [_validate_company_ticker_entry(entry) for entry in entries]


async def get_company_tickers(
    client: AsyncClient
) -> list[CompanyTickerEntry]:
    url = _build_url("/files/company_tickers_exchange.json")

    response = await client.get(url)
    data = response.json()

    return _validate_company_ticker_entries(data)


def _validate_cik_lookup_result(html: str) -> list[CompanySearchResultEntry]:
    tree = lxml.html.document_fromstring(html)
    targets = tree.xpath("//table//tr//td//pre")

    if not targets:
        return []

    table = targets[1].text_content()
    rows = table.strip().split("\n")
    entries = [row.strip().split("   ") for row in rows]
    entries = [
        CompanySearchResultEntry(cik=int(a), name=b)
        for a, b in entries
    ]

    return entries


async def lookup_cik(
    client: AsyncClient,
    query: str
) -> list[CompanySearchResultEntry]:
    url = _build_url("/cgi-bin/cik_lookup")
    data = { "company": query }

    response = await client.post(url, data=data)
    html = response.text

    return _validate_cik_lookup_result(html)
