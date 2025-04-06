import datetime

from pydantic import BaseModel


__all__ = (
    "DateRange",

    "last_n_years"
)


class DateRange(BaseModel):
    start: datetime.date
    stop: datetime.date


def last_n_years(n: int) -> DateRange:
    today = datetime.date.today()
    start = today - datetime.timedelta(days=n * 365)
    return DateRange(start=start, stop=today)
