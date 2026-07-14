# 初始的餐廳名單，保留以備餐廳名單需要回復初始狀態

from google.cloud import firestore

db = firestore.Client()

restaurants = [
    {
        "id": "r001",
        "nickname": "三寶飯",
        "fullname": "香港鴻圖燒臘",
        "URL": "https://maps.app.goo.gl/g7SkpFWHVKgk98847",
        "budget_min": 130,
        "budget_max": 200,
        "category": "taiwanese",
        "tags": ["燒臘", "便當", "乾炒牛河"],
    },
    {
        "id": "r002",
        "nickname": "鐵板燒",
        "fullname": "炙森鐵板燒",
        "URL": "https://maps.app.goo.gl/aB7hKebsGQgANUkEA",
        "budget_min": 200,
        "budget_max": 400,
        "category": "taiwanese",
        "tags": ["鐵板燒", "蛤蠣湯", "吃到飽"],
    },
    {
        "id": "r003",
        "nickname": "咖哩",
        "fullname": "咖哩炸造カレー専門店",
        "URL": "https://maps.app.goo.gl/Qdh6vmdN3qc2pYm7A",
        "budget_min": 100,
        "budget_max": 200,
        "category": "japanese",
        "tags": ["咖哩", "炸物", "味噌湯"],
    },
    {
        "id": "r004",
        "nickname": "咖哩",
        "fullname": "合江蛋包飯",
        "URL": "https://maps.app.goo.gl/NXdnaY52uFj4iMSb7",
        "budget_min": 100,
        "budget_max": 200,
        "category": "taiwanese",
        "tags": ["咖哩", "蛋包飯", "炸物"],
    },
    {
        "id": "r005",
        "nickname": "泰式火鍋",
        "fullname": "藍象廷泰式火鍋",
        "URL": "https://maps.app.goo.gl/7ov8azqh4PeiftT18",
        "budget_min": 200,
        "budget_max": 400,
        "category": "thai",
        "tags": ["火鍋", "蔬菜", "吃到飽"],
    },
    {
        "id": "r006",
        "nickname": "牛排",
        "fullname": "孫東寶台式牛排教父",
        "URL": "https://maps.app.goo.gl/d7HkKWf35sj2uiux7",
        "budget_min": 200,
        "budget_max": 400,
        "category": "taiwanese",
        "tags": ["牛排", "玉米濃湯"],
    },
    {
        "id": "r007",
        "nickname": "牛排",
        "fullname": "藍新牛屋厚切牛排",
        "URL": "https://maps.app.goo.gl/euygQfEehAuftVMT8",
        "budget_min": 200,
        "budget_max": 400,
        "category": "taiwanese",
        "tags": ["牛排", "牛肉湯", "咖哩飯"],
    },
]

for r in restaurants:
    db.collection("restaurant_list").document(r["id"]).set(r)

