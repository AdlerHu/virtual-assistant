# 未來有需要批輛新增 field 時用

from google.cloud import firestore

db = firestore.Client()

docs = db.collection("restaurant_list").stream()

for doc in docs:
    doc.reference.update({
        "last_visit_date": None
    })

print("Done")