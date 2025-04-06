import datetime

from pydantic import BaseModel


__all__ = (
    "DateRange",

    "last_n_years",
    "last_n_months"
)


class DateRange(BaseModel):
    start: datetime.date
    end: datetime.date


def last_n_years(n: int) -> DateRange:
    today = datetime.date.today()

    # TODO: leap year handling
    start = today - datetime.timedelta(days=n * 365)

    return DateRange(start=start, end=today)


def last_n_months(n: int) -> DateRange:
    today = datetime.date.today()
    start = today - datetime.timedelta(days=n * 30)

    return DateRange(start=start, end=today)
