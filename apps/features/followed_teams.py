def check_followed_teams(
    order: str,
    chat_id: int,
    db,
) -> str:
    """
    顯示目前關注的 LOL 隊伍。
    """

    lck = _get_subscription(
        db=db,
        subscription_id="lck",
    )

    worlds = _get_subscription(
        db=db,
        subscription_id="lol_worlds",
    )

    lck_teams = lck.get(
        "teams",
        [],
    )

    worlds_teams = worlds.get(
        "teams",
        [],
    )

    lines = [
        "目前關注的 LOL 隊伍：",
        "",
        "LCK：",
    ]

    if lck_teams:
        lines.append(
            "、".join(
                team.upper()
                for team in lck_teams
            )
        )
    else:
        lines.append("目前沒有關注隊伍。")

    lines.extend([
        "",
        "Worlds：",
    ])

    if worlds_teams:
        lines.append(
            "、".join(
                team.upper()
                for team in worlds_teams
            )
        )
    else:
        lines.append("目前沒有關注隊伍。")

    return "\n".join(lines)


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


def _get_subscription(
    db,
    subscription_id: str,
) -> dict:
    snapshot = (
        db.collection("subscription")
        .document(subscription_id)
        .get()
    )

    if not snapshot.exists:
        return {
            "enabled": False,
            "teams": [],
        }

    return snapshot.to_dict() or {}