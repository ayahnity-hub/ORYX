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



app = Flask(__name__)

plate_model = YOLO("best.pt")


reader = easyocr.Reader(['en'])

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = 'ayahnity@gmail.com'
app.config['MAIL_PASSWORD'] = 'hltr ufws ixnu rmmd'

mail = Mail(app)

client = MongoClient("mongodb://localhost:27017/")
db = client["oryx_db"]

face_app = FaceAnalysis(name='buffalo_l')

face_app.prepare(
    ctx_id=0,
    det_size=(320,320)
)

@app.route('/')
def home():
    return render_template("login.html")

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
        "role": "officer"  
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

    
    today = datetime.now().strftime("%A")

    shift = db.shifts.find_one({
        "email": user["email"],
        "day": today
    })

    if not shift:
        return jsonify({"message": "No shift today"}), 403

    
    now = datetime.now().hour

    start = int(shift["start"])
    end = int(shift["end"])

    if shift["period_start"] == "PM" and start != 12:
        start += 12
    if shift["period_end"] == "PM" and end != 12:
        end += 12

    
    if not (start <= now <= end):
        return jsonify({"message": "Not your shift time"}), 403
 
    otp = random.randint(100000, 999999)

    print("OTP =", otp)

    db.otps.delete_many({
    "email": user["email"]
})


    db.otps.insert_one({
    "email": user["email"],
    "otp": str(otp)
})

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
last_plate = ""
last_box = None

import time
import base64

@app.route("/detect_plate_live", methods=["POST"])
def detect_plate_live():

    global last_plate, last_box

    try:

        file = request.files["image"]

        
        file_bytes = np.frombuffer(
            file.read(),
            np.uint8
        )

        frame = cv2.imdecode(
            file_bytes,
            cv2.IMREAD_COLOR
        )

        if frame is None:

            return {
                "plate": last_plate or "No Frame",
                "confidence": 0,
                "box": last_box
            }

        results = plate_model.predict(
            source=frame,
            conf=0.25,
            imgsz=640,
            verbose=False
        )

        best_plate = ""
        best_box = None

        
        for r in results:

            boxes = r.boxes.xyxy.cpu().numpy()

            for box in boxes:

                x1, y1, x2, y2 = map(int, box)

                best_box = {
                    "x": x1,
                    "y": y1,
                    "w": x2 - x1,
                    "h": y2 - y1
                }

               
                plate = frame[y1:y2, x1:x2]

                if plate.size == 0:
                    continue

                
                plate_res = cv2.resize(
                    plate,
                    None,
                    fx=4,
                    fy=4,
                    interpolation=cv2.INTER_CUBIC
                )

                
                gray = cv2.cvtColor(
                    plate_res,
                    cv2.COLOR_BGR2GRAY
                )

                gray = cv2.GaussianBlur(
                    gray,
                    3
                )

                _, thresh = cv2.threshold(
                    gray,
                    0,
                    255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )

                ocr_res = reader.readtext(
                    thresh,
                    detail=0,
                    paragraph=False
                )

                raw_text = "".join(
                    ocr_res
                )

                raw_text = raw_text.replace(
                    " ",
                    ""
                )

                
                clean_text = "".join([
                    c for c in raw_text
                    if c.isdigit()
                ])
                if len(clean_text) < 4:
                  clean_text = ""

                
                if len(clean_text) == 6:

                    clean_text = (
                        clean_text[:2]
                        + "-"
                        + clean_text[2:]
                    )

                best_plate = clean_text

                print("PLATE =", best_plate)

   
                if len(best_plate) >= 4:
                    if best_plate != last_plate:
                       last_plate = best_plate

                if best_box:
                    last_box = best_box


                if best_box is None:

                    last_plate = ""
                    last_box = None

                return {

                    "plate":
                        last_plate
                        or "Detecting...",

                    "confidence": 0.95,

                    "box":
                        last_box

                }

       
        return {

            "plate":
                last_plate
                or "Waiting for plate...",

            "confidence": 0.95 if last_plate else 0,

            "box":
                last_box

        }

    except Exception as e:

        print("PLATE ERROR:", e)

        return {

            "plate":
                last_plate
                or "Error",

            "confidence": 0,

            "box":
                last_box

        }
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
        "user": data.get("user")    
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

    print("DATA RECEIVED:", data)  

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
        .sort("time", -1)   
        .limit(5)          
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

    db.locations.update_one(
        {"email": data["email"]},
        {"$set": data},
        upsert=True
    )

    return {"message":"saved"}

@app.route('/get_locations', methods=['GET'])
def get_locations():

    locations = list(db.locations.find({}, {"_id": 0}))

    return jsonify(locations)


@app.route("/dashboard_stats")
def dashboard_stats():

    online = db.locations.count_documents({})

    alerts = db.alerts.count_documents({})

    coverage = min(online * 20, 100)

    return jsonify({
    "online": online,
    "alerts": alerts,
    "patrols": online,
    "coverage": coverage
})


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

    try:
        get_citizen_embedding_cache(force_refresh=True)
    except NameError:
        pass

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


BASE_THRESHOLD = 0.18
LOW_Q = 0.30
HIGH_Q = 0.70
LOW_OFFSET = 0.02
HIGH_OFFSET = -0.01
MIN_THRESHOLD = 0.15
MAX_THRESHOLD = 0.60

MIN_LIVE_SIMILARITY = 0.15
MIN_TOP1_GAP = 0.00

CITIZEN_CACHE = {
    "items": [],
    "matrix": None,
    "expires_at": 0.0
}
CITIZEN_CACHE_TTL = 2.0  


def l2_normalize_vector(vector):
    vector = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(vector) + 1e-12
    return vector / norm


def get_citizen_embedding_cache(force_refresh=False):
    """Load citizen embeddings from MongoDB and cache normalized matrix for fast dot-product search."""
    now = time.time()

    if (
        not force_refresh
        and CITIZEN_CACHE["matrix"] is not None
        and now < CITIZEN_CACHE["expires_at"]
    ):
        return CITIZEN_CACHE["items"], CITIZEN_CACHE["matrix"]

    items = []
    embeddings = []

    for citizen in db.citizens.find():
        emb = citizen.get("embedding")
        if emb is None:
            continue

        try:
            emb = l2_normalize_vector(emb)
            items.append(citizen)
            embeddings.append(emb)
        except Exception as e:
            print("Skipping invalid citizen embedding:", e)

    matrix = np.vstack(embeddings).astype(np.float32) if embeddings else None

    CITIZEN_CACHE["items"] = items
    CITIZEN_CACHE["matrix"] = matrix
    CITIZEN_CACHE["expires_at"] = now + CITIZEN_CACHE_TTL

    return items, matrix


def compute_quality_features_from_image(img, bbox=None):
    """Compute brightness, contrast, and blur from the detected face crop when available."""
    if img is None or img.size == 0:
        return 127.5, 0.0, 0.0

    crop = img

    if bbox is not None:
        h, w = img.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        pad_x = int(0.08 * max(1, x2 - x1))
        pad_y = int(0.08 * max(1, y2 - y1))
        x1 = max(0, min(x1 - pad_x, w - 1))
        x2 = max(0, min(x2 + pad_x, w))
        y1 = max(0, min(y1 - pad_y, h - 1))
        y2 = max(0, min(y2 + pad_y, h))

        if x2 > x1 and y2 > y1:
            crop = img[y1:y2, x1:x2]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    return brightness, contrast, blur


def compute_live_quality_score(brightness, contrast, blur):
    """
    Fast live approximation of the notebook quality score.
    Same feature logic and weights: 0.5 blur + 0.2 contrast + 0.3 brightness suitability.
    """
    brightness_good = 1.0 - abs(brightness - 127.5) / 127.5
    brightness_good = float(np.clip(brightness_good, 0.0, 1.0))

    contrast_norm = float(np.clip(contrast / 80.0, 0.0, 1.0))
    blur_norm = float(np.clip(blur / 500.0, 0.0, 1.0))

    quality_score = (
        0.5 * blur_norm +
        0.2 * contrast_norm +
        0.3 * brightness_good
    )

    return float(np.clip(quality_score, 0.0, 1.0))


def adaptive_similarity_threshold(quality_score):
    """Adaptive threshold from the final efficient notebook configuration."""
    q = float(quality_score)

    if q <= LOW_Q:
        threshold = BASE_THRESHOLD + LOW_OFFSET
    elif q >= HIGH_Q:
        threshold = BASE_THRESHOLD + HIGH_OFFSET
    else:
        alpha = (q - LOW_Q) / (HIGH_Q - LOW_Q + 1e-12)
        offset = LOW_OFFSET * (1 - alpha) + HIGH_OFFSET * alpha
        threshold = BASE_THRESHOLD + offset

    threshold = max(threshold, MIN_LIVE_SIMILARITY)
    return float(np.clip(threshold, MIN_THRESHOLD, MAX_THRESHOLD))


def face_area(face):
    x1, y1, x2, y2 = face.bbox.astype(int)
    return max(0, x2 - x1) * max(0, y2 - y1)


def evaluate_face_match(new_embedding, img=None, bbox=None):
    """
    Evaluate one detected face against the citizen gallery.
    Returns a dictionary with match decision and scores.
    """
    citizens, gallery_matrix = get_citizen_embedding_cache()

    if gallery_matrix is None or len(citizens) == 0:
        print("No citizen embeddings found in database.")
        return {
            "accepted": False,
            "match": None,
            "best_similarity": -1.0,
            "second_similarity": -1.0,
            "gap": 0.0,
            "threshold": 1.0,
            "quality_score": 0.0,
            "margin": -999.0,
        }

    probe_embedding = l2_normalize_vector(new_embedding)

    similarities = gallery_matrix @ probe_embedding
    best_idx = int(np.argmax(similarities))
    best_similarity = float(similarities[best_idx])
    best_match = citizens[best_idx]

    if len(similarities) > 1:
        second_similarity = float(np.partition(similarities, -2)[-2])
    else:
        second_similarity = -1.0
    gap = best_similarity - second_similarity

    brightness, contrast, blur = compute_quality_features_from_image(img, bbox)
    quality_score = compute_live_quality_score(brightness, contrast, blur)
    threshold = adaptive_similarity_threshold(quality_score)

    accepted = (best_similarity >= threshold) and (gap >= MIN_TOP1_GAP or len(similarities) == 1)
    margin = best_similarity - threshold

    print("BEST:", best_match.get("name", "UNKNOWN"),
          "SIM:", round(best_similarity, 4),
          "GAP:", round(gap, 4),
          "Q:", round(quality_score, 4),
          "TH:", round(threshold, 4),
          "ACCEPT:", accepted)

    return {
        "accepted": accepted,
        "match": best_match if accepted else None,
        "candidate": best_match,
        "best_similarity": best_similarity,
        "second_similarity": second_similarity,
        "gap": gap,
        "threshold": threshold,
        "quality_score": quality_score,
        "margin": margin,
    }


def find_match(new_embedding, img=None, bbox=None):
    """Backward-compatible wrapper used by non-live endpoints."""
    result = evaluate_face_match(new_embedding, img, bbox)
    return result["match"] if result["accepted"] else None


def select_best_face_result(faces, img):
    """
    Re-evaluate every detected face in the current frame.
    This prevents the app from sticking to the first detected face when the person changes.
    """
    if not faces:
        return None, None, None

    best_accepted = None
    largest_face = max(faces, key=face_area)

    for face in faces:
        result = evaluate_face_match(face.embedding, img, face.bbox)
       
        if result["accepted"]:
            if best_accepted is None or result["margin"] > best_accepted["result"]["margin"]:
                best_accepted = {"face": face, "result": result}

    if best_accepted is not None:
        return best_accepted["face"], best_accepted["result"], best_accepted["result"]["match"]

    
    unknown_result = evaluate_face_match(largest_face.embedding, img, largest_face.bbox)
    return largest_face, unknown_result, None


def decode_uploaded_image(file):
    """Faster than saving every frame to temp.jpg."""
    file_bytes = np.frombuffer(file.read(), np.uint8)
    return cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)


@app.route("/detect_face", methods=["POST"])
def detect_face():

    file = request.files["image"]

    try:
        img = decode_uploaded_image(file)
        if img is None:
            return {"msg": "Invalid image"}

        faces = face_app.get(img)

        if len(faces) == 0:
            return {"msg": "No face found"}

        face, result, match = select_best_face_result(faces, img)

        if match:
            return {
                "name": match["name"],
                "nid": match["nid"],
                "risk": match.get("risk", "UNKNOWN"),
                "location": match.get("location", ""),
                "image": match.get("image", ""),
                "similarity": round(result["best_similarity"], 4),
                "threshold": round(result["threshold"], 4),
                "quality_score": round(result["quality_score"], 4),
            }

        return {
            "msg": "Unknown",
            "similarity": round(result["best_similarity"], 4) if result else None,
            "threshold": round(result["threshold"], 4) if result else None,
            "quality_score": round(result["quality_score"], 4) if result else None,
        }

    except Exception as e:
        return {"error": str(e)}


import cv2
import numpy as np


@app.route("/detect_face_live", methods=["POST"])
def detect_face_live():

    file = request.files["image"]

    try:
        img = decode_uploaded_image(file)
        if img is None:
            return {"face": None, "name": "Unknown", "risk": "UNKNOWN"}

        faces = face_app.get(img)

        if len(faces) == 0:
            return {"face": None, "name": "Unknown", "risk": "UNKNOWN"}

        face, result, match = select_best_face_result(faces, img)
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1

        face_box = {
            "x": int(x1),
            "y": int(y1),
            "w": int(w),
            "h": int(h)
        }

        if match:
           
            db.logs.insert_one({
                "event": "Face Recognized",
                "time": str(datetime.now()),
                "username": match["name"],
                "status": "SUCCESS"
            })

            return {
                "face": face_box,
                "name": match["name"],
                "nid": match["nid"],
                "risk": match.get("risk", "UNKNOWN"),
                "location": match.get("location", ""),
                "image": match.get("image", ""),
                "similarity": round(result["best_similarity"], 4),
                "threshold": round(result["threshold"], 4),
                "quality_score": round(result["quality_score"], 4),
                "gap": round(result["gap"], 4),
            }

        return {
            "face": face_box,
            "name": "Unknown",
            "risk": "UNKNOWN",
            "similarity": round(result["best_similarity"], 4) if result else None,
            "threshold": round(result["threshold"], 4) if result else None,
            "quality_score": round(result["quality_score"], 4) if result else None,
            "gap": round(result["gap"], 4) if result else None,
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
