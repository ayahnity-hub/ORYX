from flask import Flask, request, jsonify, render_template
from flask_mail import Mail, Message
import random
from pymongo import MongoClient
import bcrypt
import datetime
from bson import ObjectId
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine
from ultralytics import YOLO
import easyocr

# LOAD MODEL

app = Flask(__name__)

# PLATE MODEL
plate_model = YOLO("best.pt")

# OCR
# OCR Reader
plate_reader = easyocr.Reader(['en', 'ar'], gpu=False)  



# EMAIL CONFIGURATION
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = '***********'
app.config['MAIL_PASSWORD'] = '**************'

mail = Mail(app)

# 🔗 MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["oryx_db"]
# 🔥 INSIGHTFACE MODEL
face_app = FaceAnalysis(name='buffalo_l')

face_app.prepare(
    ctx_id=0,
    det_size=(640,640)
)

# 🟢 الصفحة الرئيسية
@app.route('/')
def home():
    return render_template("login.html")

# 🧑‍💻 Register API
@app.route('/register', methods=['POST'])

def register():
    data = request.json
    data = request.json
    email = data["email"]

    hashed_password = bcrypt.hashpw(
        data.get("password").encode('utf-8'),
        bcrypt.gensalt()
    )

    user = {
        "username": data.get("username"),
        "email": data.get("email"),
        "password": hashed_password,
        "role": "officer"  # 🔥 default role
    }

    db.users.insert_one(user)
    
    

    return jsonify({"message": "User registered successfully"})




from datetime import datetime

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    user = db.users.find_one({"email": data["email"]})

    if not user:
        return jsonify({"message": "User not found"}), 401

    # تحقق كلمة المرور
    if not bcrypt.checkpw(data["password"].encode('utf-8'), user["password"]):
        return jsonify({"message": "Wrong password"}), 401
    
    db.logs.insert_one({
    "time": str(datetime.now()),
    "username": user["email"],
    "role": user["role"],
    "ip": request.remote_addr,
    "event": "Login",
    "status": "SUCCESS"
})

    # 🔥 اليوم الحالي
    today = datetime.now().strftime("%A")

    # 🔥 جيب الشفت
    shift = db.shifts.find_one({
        "email": user["email"],
        "day": today
    })

    if not shift:
        return jsonify({"message": "No shift today"}), 403

    # 🔥 تحويل الوقت
    now = datetime.now().hour

    start = int(shift["start"])
    end = int(shift["end"])

    if shift["period_start"] == "PM" and start != 12:
        start += 12
    if shift["period_end"] == "PM" and end != 12:
        end += 12

    # 🔥 التحقق
    if not (start <= now <= end):
        return jsonify({"message": "Not your shift time"}), 403
    
    # GENERATE OTP
    otp = random.randint(100000, 999999)

    print("OTP =", otp)

# DELETE OLD OTP
    db.otps.delete_many({
    "email": user["email"]
})

# SAVE OTP
    db.otps.insert_one({
    "email": user["email"],
    "otp": str(otp)
})

# SEND EMAIL
    msg = Message(
    "ORYX Verification Code",
    sender=app.config['MAIL_USERNAME'],
    recipients=[user["email"]]
)

    msg.body = f"Your ORYX verification code is: {otp}"

    print("SENDING EMAIL...")

    mail.send(msg)

    print("EMAIL SENT")

    return jsonify({
    "message": "OTP sent"
})
@app.route("/detect_plate_live", methods=["POST"])
def detect_plate_live():
    try:
        file = request.files["image"]
        path = "plate_temp.jpg"
        file.save(path)

        frame = cv2.imread(path)
        if frame is None:
            return {"plate": "No Plate", "confidence": 0, "box": None}

        # حفظ الأبعاد الأصلية
        orig_h, orig_w = frame.shape[:2]

        # Resize للكشف فقط
        input_frame = cv2.resize(frame, (1280, 720))

        results = plate_model.predict(
            source=input_frame,
            conf=0.18,
            imgsz=640,
            verbose=False
        )

        best_plate = "No Plate"
        best_conf = 0
        best_box = None

        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < best_conf:
                    continue

                # إحداثيات على الصورة المُصغرة (1280x720)
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if (x2 - x1) < 70 or (y2 - y1) < 25:
                    continue

                # ================== تصحيح الإحداثيات للصورة الأصلية ==================
                scale_x = orig_w / 1280
                scale_y = orig_h / 720

                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                best_conf = conf
                best_box = {"x": x1, "y": y1, "w": x2-x1, "h": y2-y1}

                # Crop من الصورة الأصلية
                h, w = y2 - y1, x2 - x1
                plate_crop = frame[
                    max(0, y1 + int(h*0.10)): min(orig_h, y2 - int(h*0.08)),
                    max(0, x1 + int(w*0.05)): min(orig_w, x2 - int(w*0.05))
                ]

                if plate_crop.size == 0:
                    continue

                # معالجة خفيفة وسريعة
                gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                
                # OCR
                ocr_results = plate_reader.readtext(
                    gray, detail=0, allowlist='0123456789-', 
                    width_ths=0.7, height_ths=0.7
                )

                if ocr_results:
                    text = ''.join(ocr_results)
                    text = ''.join(c for c in text if c.isdigit() or c == '-')
                    text = text.strip()

                    if len(text) >= 4:
                        best_plate = text
                        print(f"✅ Plate: {best_plate} | Conf: {conf:.2f}")

        return {
            "plate": best_plate,
            "confidence": round(best_conf, 2),
            "box": best_box
        }

    except Exception as e:
        print("Plate Error:", str(e))
        return {"plate": "Error", "confidence": 0, "box": None}
@app.route('/verify_otp', methods=['POST'])
def verify_otp():

    data = request.json

    otp_record = db.otps.find_one({
        "email": data["email"],
        "otp": data["otp"]
    })

    if not otp_record:

        return jsonify({
            "message": "Invalid OTP"
        }), 401

    user = db.users.find_one({
        "email": data["email"]
    })

    db.otps.delete_many({
        "email": data["email"]
    })

    return jsonify({
        "message": "Login successful",
        "email": user["email"],
        "role": user["role"]
    })

    
from flask import request, jsonify

@app.route("/confirm_alert",methods=["POST"])
def confirm_alert():
    data = request.json

    db.logs.insert_one({
        "event":"Confirmed suspect",
        "time": str(datetime.now()),
        "user": data.get("user")
    })

    return {"msg":"ok"}


@app.route("/ignore_alert_item", methods=["POST"])
def ignore_alert_item():
    data = request.json

    db.alerts.update_one(
        {"_id": ObjectId(data["id"])},
        {"$set": {"status": "IGNORED"}}
    )

    db.logs.insert_one({
        "event": "Ignored alert",
        "time": str(datetime.now()),
        "user": data.get("user")   # 🔥 هون الإيميل
    })

    return {"msg": "ignored"}


@app.route("/mark_alert_read", methods=["POST"])
def mark_alert_read():
    data = request.json

    db.alerts.update_one(
        {"_id": ObjectId(data["id"])},
        {"$set": {"status": "READ"}}
    )

    return {"msg": "updated"}



@app.route('/add_shift', methods=['POST'])
def add_shift():
    data = request.json

    print("DATA RECEIVED:", data)  # 🔥 مهم

    db.shifts.insert_one({
        "email": data["email"],
        "day": data["day"],
        "start": data["start"],
        "end": data["end"],
        "period_start": data["period_start"],
        "period_end": data["period_end"]
    })

    return jsonify({"message": "saved"})
@app.route('/get_shifts')
def get_shifts():
    shifts = list(db.shifts.find({}, {"_id": 0}))
    return jsonify(shifts)

@app.route('/users', methods=['GET'])
def get_users():
    users = list(db.users.find({}, {"_id": 0, "password": 0}))
    return jsonify(users)
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json

    hashed_password = bcrypt.hashpw(
        data.get("password").encode('utf-8'),
        bcrypt.gensalt()
    )

    user = {
    "username": data.get("username"),
    "email": data.get("email"),
    "password": hashed_password,
    "role": data.get("role"),
    "shift_start": data.get("shift_start"),
    "shift_end": data.get("shift_end")
}

    db.users.insert_one(user)

    return jsonify({"message": "User added"})

@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    db.users.delete_one({"email": data.get("email")})
    return jsonify({"message": "User deleted"})

@app.route('/logs', methods=['GET'])
def get_logs():
    logs = list(
        db.logs.find({}, {"_id": 0})
        .sort("time", -1)   # 🔥 الأحدث أول
        .limit(5)           # 🔥 آخر 5 فقط
    )
    return jsonify(logs)

@app.route('/alerts', methods=['GET'])
def get_alerts():
    alerts = list(db.alerts.find())

    for a in alerts:
        a["_id"] = str(a["_id"])

    return jsonify(alerts)

@app.route('/update_role', methods=['POST'])
def update_role():
    data = request.json

    db.users.update_one(
        {"email": data.get("email")},
        {"$set": {"role": data.get("role")}}
    )

    return jsonify({"message": "Role updated"})

@app.route('/location', methods=['POST'])
def location():
    data = request.json

    db.locations.insert_one(data)

    return {"message": "Location saved"}

@app.route('/get_locations', methods=['GET'])
def get_locations():

    locations = list(db.locations.find({}, {"_id": 0}))

    return jsonify(locations)



@app.route("/get_my_location")
def my_location():
    return {
        "lat":31.95,
        "lng":35.91
    }

@app.route("/current_suspect")
def current_suspect():

    suspect = db.citizens.find_one()

    if not suspect:
        return {}

    return {
        "name": suspect["name"],
        "risk": suspect.get("risk","UNKNOWN"),
        "nid": suspect["nid"],
        "location": suspect.get("location",""),
        "status": "WANTED",
        "image": suspect.get("image","https://i.imgur.com/1X6YF.jpg")
    }


@app.route("/assign_alert",methods=["POST"])
def assign_alert():
    data=request.json
    db.logs.insert_one({"event":f"Assigned alert {data['id']}"})
    return {"msg":"ok"}


# 🔥 citizens collection
citizens = db.citizens

@app.route("/add_citizen", methods=["POST"])
def add_citizen():

    data = request.json

    image_path = data["image"]

    img = cv2.imread(image_path)

    faces = face_app.get(img)

    if len(faces) == 0:
        return {"msg":"No face found"}

    embedding = faces[0].embedding.tolist()

    db.citizens.insert_one({

        "name": data["name"],
        "nid": data["nid"],
        "location": data["location"],
        "image": data["image"],
        "risk": data.get("risk","UNKNOWN"),
        "embedding": embedding

    })

    return {"msg":"Citizen added"}

@app.route("/system_alerts")
def system_alerts():
    return list(db.system_alerts.find({},{"_id":0}))



from datetime import datetime

@app.route("/test_alert")
def test_alert():
    db.alerts.insert_one({
        "message": " Manual Alert Test"
    })
    return "ok"

@app.route("/test_system_alert")
def test_system_alert():
    db.system_alerts.insert_one({
        "message": " System Alert Test",
        "time": str(datetime.now())
    })
    return "ok"

@app.route("/add_system_alert", methods=["POST"])
def add_system_alert():
    data = request.json

    db.system_alerts.insert_one({
    "message": "Unauthorized access attempt",
    "time": str(datetime.now()),
    "severity": "HIGH",
    "source": "Camera 3"
})

import numpy as np

def find_match(new_embedding, threshold=0.45):

    citizens = list(db.citizens.find())

    best_match = None
    min_distance = 999

    for c in citizens:

        if "embedding" not in c:
            continue

        db_embedding = np.array(c["embedding"])

        distance = cosine(
            new_embedding,
            db_embedding
        )

        if distance < min_distance:
            min_distance = distance
            best_match = c

    print("BEST DISTANCE:", min_distance)

    if min_distance < threshold:
        return best_match

    return None


@app.route("/detect_face", methods=["POST"])
def detect_face():

    file = request.files["image"]

    path = "temp.jpg"

    file.save(path)

    try:

        img = cv2.imread(path)

        faces = face_app.get(img)

        if len(faces) == 0:
            return {"msg":"No face found"}

        embedding = faces[0].embedding

        match = find_match(embedding)

        if match:

            return {
                "name": match["name"],
                "nid": match["nid"],
                "risk": match["risk"],
                "location": match.get("location",""),
                "image": match.get("image","")
            }

        return {"msg":"Unknown"}

    except Exception as e:
        return {"error": str(e)}


import cv2
import numpy as np





@app.route("/detect_face_live", methods=["POST"])
def detect_face_live():

    file = request.files["image"]

    path = "temp.jpg"

    file.save(path)

    try:

        img = cv2.imread(path)

        faces = face_app.get(img)

        if len(faces) == 0:
            return {"face": None}

        face = faces[0]

        bbox = face.bbox.astype(int)

        x1,y1,x2,y2 = bbox

        w = x2 - x1
        h = y2 - y1

        embedding = face.embedding

        match = find_match(embedding)

        if match:

            # 🔥 سجل لوق
            db.logs.insert_one({
                "event":"Face Recognized",
                "time": str(datetime.now()),
                "username": match["name"],
                "status":"SUCCESS"
            })

            return {

                "face":{
                    "x":int(x1),
                    "y":int(y1),
                    "w":int(w),
                    "h":int(h)
                },

                "name": match["name"],
                "nid": match["nid"],
                "risk": match.get("risk","UNKNOWN"),
                "location": match.get("location",""),
                "image": match.get("image","")

            }

        return {

            "face":{
                "x":int(x1),
                "y":int(y1),
                "w":int(w),
                "h":int(h)
            },

            "name":"Unknown",
            "risk":"UNKNOWN"

        }

    except Exception as e:

        return {"error": str(e)}
from flask import send_file

from flask import send_file
import os

@app.route("/get_image")
def get_image():

    path = request.args.get("path")

    print("IMAGE PATH =", path)
    print("FILE EXISTS =", os.path.exists(path))

    return send_file(path)
# 🟢 صفحات
@app.route('/admin')
def admin():
    return render_template("admin.html")

@app.route('/police')
def police():
    return render_template("police.html")

@app.route('/officer')
def officer():
    return render_template("officer.html")

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
