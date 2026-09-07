import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from google.cloud import firestore


CITO_API_KEY = os.environ["CITO_API_KEY"]

CITO_API_URL = (
    "https://api.citoapi.com/api/v1"
    "/lol/leagues/lol-worlds/schedule"
)

TIMEZONE = ZoneInfo("Asia/Taipei")


def load_world_history():
    db = firestore.Client()

    events = get_worlds_history()

    saved = 0
    skipped = 0

    for event in events:
        match = parse_worlds_match(event)

        if match is None:
            skipped += 1
            continue

        match_id = match["match_id"]

        doc_ref = (
            db.collection("world_history")
            .document(match_id)
        )

        doc_ref.set(
            {
                **match,
                "source": "cito",
                "updated_at":
                    firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        saved += 1

    return {
        "received": len(events),
        "saved": saved,
        "skipped": skipped,
    }


def get_worlds_history() -> list[dict]:
    response = requests.get(
        CITO_API_URL,
        headers={
            "x-api-key": CITO_API_KEY,
        },
        params={
            "state": "completed",
            "from": "2025-10-01",
            "to": "2025-11-15",
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

    return (
        result
        .get("data", {})
        .get("events", [])
    )


def parse_worlds_match(
    event: dict,
) -> dict | None:
    match_id = event.get("matchId")

    if not match_id:
        return None

    start_time_raw = event.get(
        "startTime"
    )

    if not start_time_raw:
        return None

    teams = event.get(
        "teams",
        []
    )

    if len(teams) != 2:
        return None

    start_time = _parse_start_time(
        start_time_raw
    )

    return {
        "match_id": match_id,

        "league": "worlds",

        "tournament_id":
            event.get("tournamentId"),

        "state":
            event.get("state"),

        "block_name":
            event.get("blockName"),

        "event_at":
            start_time,

        "team1": (
            teams[0].get("code")
            or teams[0].get("name")
        ),

        "team2": (
            teams[1].get("code")
            or teams[1].get("name")
        ),

        "team1_slug":
            teams[0].get("slug"),

        "team2_slug":
            teams[1].get("slug"),

        "best_of": (
            event
            .get("strategy", {})
            .get("count")
        ),
    }


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


if __name__ == "__main__":
    result = load_world_history()

    print(result)