# 與口袋名單有關的功能放在這裡，包括對口袋名單查看、新增、修改、刪除，以及好手氣功能


def check_list_restaurants(db):
    docs = db.collection("restaurant_list").stream()

    rows = []
    # for doc in docs:
    #     r = doc.to_dict()
    #     rows.append(
    #         f"{r.get('nickname', doc.id)}｜{r.get('fullname', '-')}｜{r.get('category', '-')}"
    #         f"｜${r.get('budget_min', '?')}-{r.get('budget_max', '?')}"
    #     )

    for doc in docs:
        r = doc.to_dict()
        rows.append(
            f'Nickname: {r.get("nickname", "-")}'
            f'Fullname: {r.get("fullname", "-")}'
            f'Category: {r.get("category", "-")}'
            f'Last Visit: {r.get("last_visit_date", "-")}'
            f'Budget: {r.get("budget_max", "-")}'
            f'------'
        )

    if not rows:
        return "目前沒有餐廳資料。"

    return "餐廳清單：\n\n" + "\n".join(rows)


def add_restaurant_list():
    return '新增餐廳名單功能建置中...'


def alter_restaurant_list():
    return '修改餐廳名單功能建置中...'


def del_restaurant_list():
    return '修改餐廳名單功能建置中...'


def surprise_me():
    return '好手氣功能建置中...'
