def check_followed_teams(order: str, chat_id: int, db) -> str:
    return (
        "CHECK_FOLLOWED_TEAMS\n"
        f"order: {order}"
    )


def add_followed_team(order: str, chat_id: int, db) -> str:
    return (
        "ADD_FOLLOWED_TEAM\n"
        f"order: {order}"
    )


def remove_followed_team(order: str, chat_id: int, db) -> str:
    return (
        "REMOVE_FOLLOWED_TEAM\n"
        f"order: {order}"
    )