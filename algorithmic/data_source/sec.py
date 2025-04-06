import datetime

from enum import StrEnum, auto
from typing import Optional

import lxml.html

from httpx import AsyncClient
from pydantic import BaseModel

from ..common.date_time import DateRange, last_n_years
from ..common.http import DEFAULT_USER_AGENT


MAIN_SEC_URL = "https://www.sec.gov"
EFTS_SEC_URL = "https://efts.sec.gov"


class FormType(StrEnum):
    F_10_K = auto()
    F_10_Q = auto()
    F_8_K = auto()

    F_S_1 = auto()


FORM_CODES = {
    FormType.F_10_K: "10-K",
    FormType.F_10_Q: "10-Q",
    FormType.F_8_K: "8-K",
    FormType.F_S_1: "S-1"
}


def _build_main_url(path: str) -> str:
    return MAIN_SEC_URL + path


def _build_efts_url(path: str) -> str:
    return EFTS_SEC_URL + path


def _build_filing_url(id: str) -> str:
    rest, name = id.split(":")
    formatted_cik, year, number = rest.split("-")
    cik = int(formatted_cik)
    path = f"/Archives/edgar/data/{cik}/{formatted_cik}{year}{number}/{name}"

    return _build_main_url(path)


def build_http_headers(user_agent: Optional[str] = None) -> dict[str, str]:
    return {
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-Gpc": "1",
        "User-Agent": user_agent or DEFAULT_USER_AGENT
    }


def format_cik(cik: int) -> str:
    return "{:010d}".format(cik)


def format_form_type(form_type: FormType) -> str:
    return FORM_CODES[form_type]


class CompanySearchResultEntry(BaseModel):
    cik: int
    name: str


class CompanyTickerEntry(BaseModel):
    cik: int
    name: str
    ticker: str
    exchange: Optional[str]


class FilingSearchResultEntry(BaseModel):
    id: str
    filed_at: datetime.date
    period_end: datetime.date


class FilingSearchResult(BaseModel):
    entries: list[FilingSearchResultEntry]


def _validate_company_ticker_entry(item: list) -> CompanyTickerEntry:
    cik, name, ticker, exchange = item

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
    url = _build_main_url("/files/company_tickers_exchange.json")

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
    url = _build_main_url("/cgi-bin/cik_lookup")
    data = {"company": query}

    response = await client.post(url, data=data)
    html = response.text

    return _validate_cik_lookup_result(html)


def _validate_filing_search_result_entry(
    item: dict
) -> FilingSearchResultEntry:
    def parse_date(x: str) -> datetime.date:
        return datetime.datetime.strptime(x, "%Y-%m-%d").date()

    id = item["_id"]
    source = item["_source"]
    filed_at = parse_date(source["file_date"])
    period_end = parse_date(source["period_ending"])

    return FilingSearchResultEntry(
        id=id,
        filed_at=filed_at,
        period_end=period_end
    )


def _validate_filing_search_result(data: dict) -> FilingSearchResult:
    entries = [
        _validate_filing_search_result_entry(item)
        for item in data["hits"]["hits"]
    ]

    return FilingSearchResult(entries=entries)


async def search_filings(
    *,
    client: AsyncClient,
    query: Optional[str] = None,
    entity: Optional[str] = None,
    ciks: list[int] = [],
    date_range: DateRange = last_n_years(1),
    form_types: list[FormType] = []
) -> dict:
    if not query and not entity and not ciks:
        raise ValueError(
            "At least one of 'query', 'entity' or 'ciks' arguments must be "
            "provided."
        )

    url = _build_efts_url("/LATEST/search-index")
    params = {}

    if query:
        params["q"] = query
    
    if entity:
        params["entityName"] = entity

    if ciks:
        params["ciks"] = ",".join(map(format_cik, ciks))

    if form_types:
        params["forms"] = ",".join(map(format_form_type, form_types))

    params["startdt"] = date_range.start.strftime("%Y-%m-%d")
    params["enddt"] = date_range.end.strftime("%Y-%m-%d")

    reponse = await client.get(url, params=params)
    data = reponse.json()

    return _validate_filing_search_result(data)


async def download_filing(
    client: AsyncClient,
    id: str
) -> str:
    url = _build_filing_url(id)
    response = await client.get(url)

    return response.text
