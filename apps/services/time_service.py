from datetime import datetime
from zoneinfo import ZoneInfo


DEFAULT_TIMEZONE = "Asia/Taipei"


def get_timezone(
    timezone_name: str,
) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def now_local(
    timezone_name: str = DEFAULT_TIMEZONE,
) -> datetime:
    return datetime.now(
        get_timezone(timezone_name)
    )


def to_local(
    value: datetime,
    timezone_name: str,
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
    timezone_name: str,
    fmt: str = "%Y/%m/%d %H:%M",
) -> str:
    local_time = to_local(
        value=value,
        timezone_name=timezone_name,
    )

    return local_time.strftime(fmt)


def get_user_timezone(
    db,
    chat_id: int,
) -> str:
    """
    從 Firestore 取得使用者 timezone。

    users/{chat_id}
        timezone: Asia/Taipei

    找不到時預設 Asia/Taipei。
    """

    doc = (
        db.collection("users")
        .document(str(chat_id))
        .get()
    )

    if not doc.exists:
        return DEFAULT_TIMEZONE

    data = doc.to_dict() or {}

    return (
        data.get("timezone")
        or DEFAULT_TIMEZONE
    )