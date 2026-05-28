import os
import random
import cv2
from pymongo import MongoClient
from insightface.app import FaceAnalysis

# 🔗 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["oryx_db"]

# 🔥 تحميل مودل InsightFace
face_app = FaceAnalysis(name='buffalo_l')

face_app.prepare(
    ctx_id=0,
    det_size=(640,640)
)

DATASET_PATH = r"C:\Users\aya23\Desktop\oryx-project\SCface_database\mugshot_frontal_cropped_all"

def generate_name(i):
    return f"Person_{i}"

citizens = []

for i, file in enumerate(os.listdir(DATASET_PATH)):

    if not file.lower().endswith((".jpg",".png",".jpeg")):
        continue

    img_path = os.path.join(DATASET_PATH, file)

    try:

        img = cv2.imread(img_path)

        faces = face_app.get(img)

        if len(faces) == 0:
            print(f"❌ No face found: {file}")
            continue

        embedding = faces[0].embedding.tolist()

        citizen = {

            "name": generate_name(i),
            "nid": str(100000000 + i),
            "image": img_path.replace("\\","/"),
            "location": random.choice(["Amman","Irbid","Zarqa"]),
            "risk": random.choice(["WANTED","SAFE"]),
            "embedding": embedding

        }

        citizens.append(citizen)

        print(f"✅ Processed {file}")

    except Exception as e:
        print("❌ Error:", file, e)

# 🔥 حذف الداتا القديمة
db.citizens.delete_many({})

# 🔥 إدخال الداتا الجديدة
if citizens:
    db.citizens.insert_many(citizens)

print("🔥 DONE:", len(citizens))
