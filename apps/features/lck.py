import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from datetime import timedelta

from google.cloud import firestore

from apps.services.task_queue import create_reminder_task


CITO_API_KEY = os.environ["CITO_API_KEY"]
CITO_API_BASE_URL = "https://api.citoapi.com/api/v1"
TIMEZONE = ZoneInfo("Asia/Taipei")

LCK_MAIN_TEAM_SLUGS = {
    "dk",
    "kt",
    "bfx",
    "hle",
    "ns",
    "t1",
    "gen",
    "bro",
    "krx"
}

def sync_lck_reminders(
    db,
    chat_id: int,
) -> dict:
    subscription = get_lck_subscription(db)

    if not subscription["enabled"]:
        return {
            "created": 0,
            "skipped": 0,
            "message": "LCK subscription is disabled.",
        }

    remind_before_minutes = subscription[
        "remind_before_minutes"
    ]

    matches = get_lck_matches(db)

    created = 0
    skipped = 0

    for match in matches:
        match_id = match["match_id"]

        if not match_id:
            continue

        doc_ref = (
            db.collection("auto_reminders")
            .document(match_id)
        )

        existing = doc_ref.get()

        if existing.exists:
            skipped += 1
            continue

        event_at = match["start_time"]

        notify_at = (
            event_at
            - timedelta(
                minutes=remind_before_minutes
            )
        )

        team1 = (
            match["team1"]["code"]
            or match["team1"]["name"]
        )

        team2 = (
            match["team2"]["code"]
            or match["team2"]["name"]
        )

        event_text = (
            f"LCK：{team1} vs {team2}"
        )

        try:
            task_name = create_reminder_task(
                chat_id=chat_id,
                reminder_text=event_text,
                event_at=event_at,
                notify_at=notify_at,
            )

            doc_ref.set({
                "type": "lck",
                "source": "cito",

                "match_id": match_id,

                "team1": team1,
                "team2": team2,

                "team1_slug": match["team1"]["slug"],
                "team2_slug": match["team2"]["slug"],

                "event_text": event_text,

                "event_at": event_at,
                "notify_at": notify_at,

                "status": "scheduled",

                "task_name": task_name,

                "created_at":
                    firestore.SERVER_TIMESTAMP,
            })

            created += 1

        except Exception as exc:
            print(
                "Failed to create LCK reminder: "
                f"match_id={match_id}, "
                f"error={exc}"
            )

    return {
        "created": created,
        "skipped": skipped,
        "total_matches": len(matches),
    }


def get_lck_subscription(db) -> dict:
    doc = (
        db.collection("subscription")
        .document("lck")
        .get()
    )

    if not doc.exists:
        return {
            "enabled": False,
            "teams": [],
            "remind_before_minutes": 15,
        }

    data = doc.to_dict() or {}

    return {
        "enabled": data.get("enabled", False),
        "teams": data.get("teams", []),
        "remind_before_minutes": data.get(
            "remind_before_minutes",
            15,
        ),
    }


def get_lck_matches(db) -> list[dict]:
    subscription = get_lck_subscription(db)

    if not subscription["enabled"]:
        return []

    watch_team_slugs = set(
        subscription["teams"]
    )

    url = (
        f"{CITO_API_BASE_URL}"
        "/lol/leagues/lol-lck/schedule"
    )

    response = requests.get(
        url,
        headers={
            "x-api-key": CITO_API_KEY,
        },
        params={
            "limit": 100,
        },
        timeout=15,
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(
            f"Cito API returned an error: {result}"
        )

    events = (
        result
        .get("data", {})
        .get("events", [])
    )

    matches = []

    LCK_MAIN_TOURNAMENT_ID = "lol-lck_split_3_2026"

    for event in events:
        if event.get("state") != "unstarted":
            continue

        # 只保留 LCK 一軍主賽事
        if event.get("tournamentId") != LCK_MAIN_TOURNAMENT_ID:
            continue

        teams = event.get("teams", [])

        if len(teams) != 2:
            continue

        team_slugs = {
            team.get("slug")
            for team in teams
        }

        # 排除 Challengers / Academy 等非 LCK 一軍賽事
        if not team_slugs.issubset(LCK_MAIN_TEAM_SLUGS):
            continue

        if not (
            watch_team_slugs
            & team_slugs
        ):
            continue

        start_time_raw = event.get(
            "startTime"
        )

        if not start_time_raw:
            continue

        start_time = _parse_start_time(
            start_time_raw
        )

        matches.append({
            "match_id": event.get("matchId"),
            "tournament_id": event.get("tournamentId"),
            "start_time": start_time,

            "team1": {
                "slug": teams[0].get("slug"),
                "code": teams[0].get("code"),
                "name": teams[0].get("name"),
            },

            "team2": {
                "slug": teams[1].get("slug"),
                "code": teams[1].get("code"),
                "name": teams[1].get("name"),
            },

            "best_of": (
                event
                .get("strategy", {})
                .get("count")
            ),

            "block_name": event.get(
                "blockName"
            ),
        })

    matches.sort(
        key=lambda match: match["start_time"]
    )

    return matches


def _parse_start_time(
    value: str,
) -> datetime:
    utc_time = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    return utc_time.astimezone(
        TIMEZONE
    )


def format_lck_matches(
    matches: list[dict],
) -> str:
    if not matches:
        return "目前沒有符合條件的 LCK 賽事。"

    lines = [
        f"找到 {len(matches)} 場符合條件的 LCK 賽事："
    ]

    for index, match in enumerate(
        matches,
        start=1,
    ):
        start_time = match["start_time"]

        team1 = (
            match["team1"]["code"]
            or match["team1"]["name"]
        )

        team2 = (
            match["team2"]["code"]
            or match["team2"]["name"]
        )

        best_of = match["best_of"]

        line = (
            f"{index}. "
            f"{start_time:%Y/%m/%d %H:%M}｜"
            f"{team1} vs {team2}"
        )

        if best_of:
            line += f"｜BO{best_of}"

        lines.append(line)

    return "\n".join(lines)