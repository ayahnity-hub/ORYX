# Environment Setup

## Python Version

Python 3.11 is recommended.

---

## Install Required Libraries

```bash
pip install -r requirements.txt
```

---

## Main Libraries Used

### Flask

```bash
pip install flask
```

### MongoDB Driver

```bash
pip install pymongo
```

### OpenCV

```bash
pip install opencv-python
```

### InsightFace

```bash
pip install insightface
```

### YOLO

```bash
pip install ultralytics
```

### EasyOCR

```bash
pip install easyocr
```

### PaddleOCR

```bash
pip install paddleocr
```

---

## Database Setup

MongoDB connection:

```text
mongodb://localhost:27017/
```

Database name:

```text
oryx_db
```

---

## Run the Project

```bash
python app.py
```

---

## Default URL

```text
http://127.0.0.1:5000
```

---

## Notes

- Make sure best.pt exists
- MongoDB must be running
- Camera permissions must be enabled
