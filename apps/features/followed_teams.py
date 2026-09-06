from google.cloud import firestore

from apps.services.followed_team_parser import (
    parse_followed_team,
)


def check_followed_teams(
    order: str,
    chat_id: int,
    db,
) -> str:
    scope = _detect_subscription_scope(
        order
    )

    if scope == "lck":
        teams = _get_followed_teams(
            db=db,
            subscription_id="lck",
        )

        return _format_team_list(
            title="LCK",
            teams=teams,
        )

    if scope == "lol_worlds":
        teams = _get_followed_teams(
            db=db,
            subscription_id="lol_worlds",
        )

        return _format_team_list(
            title="Worlds",
            teams=teams,
        )

    lck_teams = _get_followed_teams(
        db=db,
        subscription_id="lck",
    )

    worlds_teams = _get_followed_teams(
        db=db,
        subscription_id="lol_worlds",
    )

    return "\n\n".join([
        _format_team_list(
            title="LCK",
            teams=lck_teams,
        ),
        _format_team_list(
            title="Worlds",
            teams=worlds_teams,
        ),
    ])


def add_followed_team(
    order: str,
    chat_id: int,
    db,
) -> str:
    try:
        team = parse_followed_team(
            order
        )

    except Exception as exc:
        print(
            "Failed to parse followed team: "
            f"{exc}"
        )

        return (
            "我無法辨識你想加入的隊伍。"
        )

    scope = _detect_subscription_scope(
        order
    )

    if scope == "lck":
        _add_team(
            db=db,
            subscription_id="lck",
            team=team,
        )

        return (
            f"已將 {team.upper()} "
            "加入 LCK 關注隊伍。"
        )

    if scope == "lol_worlds":
        _add_team(
            db=db,
            subscription_id="lol_worlds",
            team=team,
        )

        return (
            f"已將 {team.upper()} "
            "加入 Worlds 關注隊伍。"
        )

    _add_team(
        db=db,
        subscription_id="lck",
        team=team,
    )

    _add_team(
        db=db,
        subscription_id="lol_worlds",
        team=team,
    )

    return (
        f"已將 {team.upper()} "
        "加入 LCK 與 Worlds 關注隊伍。"
    )


def remove_followed_team(
    order: str,
    chat_id: int,
    db,
) -> str:
    try:
        team = parse_followed_team(
            order
        )

    except Exception as exc:
        print(
            "Failed to parse followed team: "
            f"{exc}"
        )

        return (
            "我無法辨識你想移除的隊伍。"
        )

    scope = _detect_subscription_scope(
        order
    )

    if scope == "lck":
        _remove_team(
            db=db,
            subscription_id="lck",
            team=team,
        )

        return (
            f"已將 {team.upper()} "
            "從 LCK 關注隊伍移除。"
        )

    if scope == "lol_worlds":
        _remove_team(
            db=db,
            subscription_id="lol_worlds",
            team=team,
        )

        return (
            f"已將 {team.upper()} "
            "從 Worlds 關注隊伍移除。"
        )

    _remove_team(
        db=db,
        subscription_id="lck",
        team=team,
    )

    _remove_team(
        db=db,
        subscription_id="lol_worlds",
        team=team,
    )

    return (
        f"已將 {team.upper()} "
        "從 LCK 與 Worlds 關注隊伍移除。"
    )


def _detect_subscription_scope(
    order: str,
) -> str:
    text = order.lower()

    if "lck" in text:
        return "lck"

    if (
        "世界賽" in text
        or "worlds" in text
        or "world championship" in text
    ):
        return "lol_worlds"

    return "all"


def _get_followed_teams(
    db,
    subscription_id: str,
) -> list[str]:
    snapshot = (
        db.collection("subscription")
        .document(subscription_id)
        .get()
    )

    if not snapshot.exists:
        return []

    data = snapshot.to_dict() or {}

    teams = data.get(
        "teams",
        [],
    )

    return sorted(
        {
            str(team).lower()
            for team in teams
            if team
        }
    )


def _add_team(
    db,
    subscription_id: str,
    team: str,
) -> None:
    doc_ref = (
        db.collection("subscription")
        .document(subscription_id)
    )

    doc_ref.set(
        {
            "teams": firestore.ArrayUnion(
                [team]
            )
        },
        merge=True,
    )


def _remove_team(
    db,
    subscription_id: str,
    team: str,
) -> None:
    doc_ref = (
        db.collection("subscription")
        .document(subscription_id)
    )

    doc_ref.update({
        "teams": firestore.ArrayRemove(
            [team]
        )
    })


def _format_team_list(
    title: str,
    teams: list[str],
) -> str:
    if not teams:
        return (
            f"{title}：\n"
            "目前沒有關注隊伍。"
        )

    team_text = "、".join(
        team.upper()
        for team in teams
    )

    return (
        f"{title}：\n"
        f"{team_text}"
    )