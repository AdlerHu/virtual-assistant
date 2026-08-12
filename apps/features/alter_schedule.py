from datetime import datetime, timedelta

from google.cloud import firestore

from apps.services.schedule_alter_parser import (
    ParsedScheduleAlter,
    ScheduleAction,
    ScheduleAlterParseError,
    parse_schedule_alter,
)
from apps.services.task_queue import (
    create_reminder_task,
    delete_reminder_task,
)
from apps.services.time_service import (
    format_local,
    get_user_timezone,
    now_local,
    to_local,
)


def alter_schedule(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    修改或取消既有行程。
    """

    timezone_name = get_user_timezone(
        db=db,
        chat_id=chat_id,
    )

    try:
        parsed = parse_schedule_alter(
            order=order,
            timezone_name=timezone_name,
        )

    except ScheduleAlterParseError as exc:
        print(
            f"Schedule alter parse error: {exc}"
        )

        return (
            "我無法辨識你想修改哪個行程，"
            "請提供行程名稱或時間。"
        )

    matches = _find_matching_schedules(
        parsed=parsed,
        chat_id=chat_id,
        db=db,
        timezone_name=timezone_name,
    )

    if not matches:
        return (
            f"找不到符合「{parsed.event_text}」"
            "的行程。"
        )

    #
    # 第一版：
    # 如果有多筆符合，不要擅自全部修改。
    #
    if len(matches) > 1:
        return _format_multiple_matches(
            matches=matches,
            timezone_name=timezone_name,
        )

    doc, data = matches[0]

    if parsed.action == ScheduleAction.CANCEL:
        return _cancel_schedule(
            doc=doc,
            data=data,
            timezone_name=timezone_name,
        )

    if parsed.action == ScheduleAction.RESCHEDULE:
        return _reschedule_schedule(
            doc=doc,
            data=data,
            parsed=parsed,
            timezone_name=timezone_name,
        )

    return "無法辨識行程修改方式。"


def _find_matching_schedules(
    parsed: ParsedScheduleAlter,
    chat_id: int,
    db,
    timezone_name: str,
):
    """
    找出可能符合的既有行程。

    第一版策略：

    1. 只找這個 chat_id
    2. 排除 cancelled
    3. 只找現在之後的行程
    4. 用 event_text 做名稱比對
    5. 如果使用者有指定日期/時間，再進一步過濾
    """

    now = now_local(timezone_name)

    docs = (
        db.collection("reminders")
        .where("chat_id", "==", chat_id)
        .where("event_at", ">=", now)
        .stream()
    )

    matches = []

    search_text = _normalize_text(
        parsed.event_text
    )

    for doc in docs:
        data = doc.to_dict()

        if data.get("status") == "cancelled":
            continue

        event_text = data.get("event_text")
        event_at = data.get("event_at")

        if (
            not event_text
            or event_at is None
        ):
            continue

        #
        # Firestore Timestamp 讀回後先轉成
        # 使用者 local timezone。
        #
        event_at_local = to_local(
            event_at,
            timezone_name,
        )

        #
        # 行程名稱比對
        #
        stored_text = _normalize_text(
            event_text
        )

        if not _text_matches(
            search_text,
            stored_text,
        ):
            continue

        #
        # 使用者有指定原行程日期
        #
        if parsed.target_date is not None:
            target_date_local = to_local(
                parsed.target_date,
                timezone_name,
            )

            if (
                event_at_local.date()
                != target_date_local.date()
            ):
                continue

        #
        # 使用者有指定原行程時間
        #
        if parsed.target_time is not None:
            event_time = event_at_local.strftime(
                "%H:%M"
            )

            if event_time != parsed.target_time:
                continue

        matches.append(
            (doc, data)
        )

    matches.sort(
        key=lambda item: item[1]["event_at"]
    )

    return matches

def _normalize_text(
    text: str,
) -> str:
    return (
        text
        .strip()
        .lower()
        .replace(" ", "")
    )


def _text_matches(
    search_text: str,
    stored_text: str,
) -> bool:
    """
    第一版簡單 substring matching。

    「雙週會」
    可以找到
    「技術部雙週會」
    """

    return (
        search_text in stored_text
        or stored_text in search_text
    )


def _cancel_schedule(
    doc,
    data: dict,
    timezone_name: str,
) -> str:

    task_name = data.get("task_name")

    try:
        if task_name:
            delete_reminder_task(
                task_name=task_name,
            )

        doc.reference.update({
            "status": "cancelled",
            "updated_at":
                firestore.SERVER_TIMESTAMP,
        })

    except Exception as exc:
        print(
            "Failed to cancel schedule: "
            f"document_id={doc.id}, "
            f"error={exc}"
        )

        return "取消行程時發生錯誤，請稍後再試。"

    event_at = data.get("event_at")
    event_text = data.get(
        "event_text",
        "未命名行程",
    )

    event_time = format_local(
        event_at,
        timezone_name=timezone_name,
        fmt="%Y/%m/%d %H:%M",
    )

    return (
        f"已取消行程：\n"
        f"{event_time}｜{event_text}"
    )


def _reschedule_schedule(
    doc,
    data: dict,
    parsed: ParsedScheduleAlter,
    timezone_name: str,
) -> str:

    old_event_at = data.get("event_at")
    old_notify_at = data.get("notify_at")
    event_text = data.get("event_text")

    if (
        old_event_at is None
        or old_notify_at is None
        or not event_text
    ):
        return "原行程資料不完整，無法修改。"

    old_event_local = to_local(
        old_event_at,
        timezone_name,
    )

    old_notify_local = to_local(
        old_notify_at,
        timezone_name,
    )

    #
    # 原本提前多久提醒
    #
    original_reminder_offset = (
        old_event_local
        - old_notify_local
    )

    try:
        new_event_at = _build_new_event_at(
            old_event_at=old_event_local,
            parsed=parsed,
            timezone_name=timezone_name,
        )

    except ValueError as exc:
        print(
            f"Failed to calculate new event time: {exc}"
        )

        return "無法判斷新的行程時間。"

    #
    # 使用者有明確指定新的提醒間隔
    #
    if (
        parsed.reminder_minutes_before
        is not None
    ):
        reminder_offset = timedelta(
            minutes=(
                parsed.reminder_minutes_before
            )
        )

    #
    # 沒有指定 → 沿用原本提醒間隔
    #
    else:
        reminder_offset = (
            original_reminder_offset
        )

    new_notify_at = (
        new_event_at - reminder_offset
    )

    now = now_local(timezone_name)

    if new_notify_at <= now:
        return (
            "新的提醒時間已經過去，"
            "因此沒有修改行程。"
        )

    old_task_name = data.get(
        "task_name"
    )

    new_task_name = None

    try:
        #
        # 先建立新的 task。
        #
        # 這樣如果建立失敗，
        # 舊 task 還存在。
        #
        new_task_name = create_reminder_task(
            chat_id=data["chat_id"],
            reminder_text=event_text,
            event_at=new_event_at,
            notify_at=new_notify_at,
        )

        #
        # 新 task 成功後才刪舊 task
        #
        if old_task_name:
            delete_reminder_task(
                task_name=old_task_name,
            )

        #
        # 最後更新 Firestore
        #
        doc.reference.update({
            "event_at": new_event_at,
            "notify_at": new_notify_at,
            "task_name": new_task_name,
            "status": "scheduled",
            "updated_at":
                firestore.SERVER_TIMESTAMP,
        })

    except Exception as exc:
        print(
            "Failed to reschedule: "
            f"document_id={doc.id}, "
            f"error={exc}"
        )

        #
        # 如果新 task 已建立，
        # 但後面的操作失敗，
        # 嘗試把新 task 清掉。
        #
        if new_task_name:
            try:
                delete_reminder_task(
                    task_name=new_task_name,
                )
            except Exception:
                pass

        return "修改行程時發生錯誤，請稍後再試。"

    event_time = format_local(
        new_event_at,
        timezone_name=timezone_name,
        fmt="%Y/%m/%d %H:%M",
    )

    notify_time = format_local(
        new_notify_at,
        timezone_name=timezone_name,
        fmt="%Y/%m/%d %H:%M",
    )

    return (
        f"已修改行程：\n"
        f"{event_time}｜{event_text}\n"
        f"提醒時間：{notify_time}"
    )


def _build_new_event_at(
    old_event_at: datetime,
    parsed: ParsedScheduleAlter,
    timezone_name: str,
) -> datetime:

    timezone = old_event_at.tzinfo

    #
    # 「改明天同樣時間」
    #
    if parsed.keep_original_time:
        if parsed.new_event_at is None:
            raise ValueError(
                "缺少新的日期"
            )

        new_date = to_local(
            parsed.new_event_at,
            timezone_name,
        ).date()

        return datetime.combine(
            new_date,
            old_event_at.timetz(),
        )

    if parsed.new_event_at is None:
        raise ValueError(
            "缺少新的行程時間"
        )

    if parsed.new_time is not None:
        hour, minute = map(
            int,
            parsed.new_time.split(":"),
        )

        return old_event_at.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

    parsed_new = to_local(
        parsed.new_event_at,
        timezone_name,
    )

    #
    # parser 給了新的日期 + 時間，
    # 直接使用。
    #
    return parsed_new

