def check_followed_teams(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    查詢目前關注的 LOL 隊伍。

    未指定賽事：
        顯示 LCK + Worlds

    指定 LCK：
        只顯示 LCK

    指定世界賽：
        只顯示 Worlds
    """

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

    # 沒有指定賽事 → 兩份都顯示
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
    return "add followed teams upcoming..."


def remove_followed_team(
    order: str,
    chat_id: int,
    db,
) -> str:
    return "remove followed teams upcoming..."


def _detect_subscription_scope(
    order: str,
) -> str:
    """
    判斷使用者指定的賽事。

    return:
        lck
        lol_worlds
        all
    """

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
        []
    )

    return sorted(
        {
            str(team).lower()
            for team in teams
            if team
        }
    )


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