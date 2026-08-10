from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Taipei"


def get_timezone(timezone_name: str = DEFAULT_TIMEZONE) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def now(timezone_name: str = DEFAULT_TIMEZONE) -> datetime:
    return datetime.now(
        get_timezone(timezone_name)
    )


def to_local(
    value: datetime,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> datetime:
    if value.tzinfo is None:
        raise ValueError(
            "datetime 必須包含 timezone"
        )

    return value.astimezone(
        get_timezone(timezone_name)
    )


def format_local(
    value: datetime,
    timezone_name: str = DEFAULT_TIMEZONE,
    fmt: str = "%Y/%m/%d %H:%M",
) -> str:
    return to_local(
        value,
        timezone_name,
    ).strftime(fmt)
