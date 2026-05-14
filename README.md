# ORYX
## AI-Powered Real-Time Security & Threat Detection System

ORYX is an advanced AI-powered surveillance and identification platform developed to support security forces in fast-paced and high-risk environments. The system combines artificial intelligence, computer vision, facial recognition, and live monitoring technologies to enhance situational awareness and improve decision-making during critical operations.

The project addresses the limitations of traditional surveillance systems by enabling real-time identification through wearable devices, live cameras, and mobile platforms. ORYX provides instant alerts, citizen identification, threat classification, and patrol monitoring in a unified intelligent system.

---

# Key Features

- Real-Time Facial Recognition
- AI-Based Threat Detection
- License Plate Detection
- Live Camera Monitoring
- GPS Tracking & Patrol Monitoring
- OTP Email Verification System
- Multi-Role Dashboard System
- Live Incident & System Alerts
- Citizen Database Management
- Real-Time Recognition Logs
- Role-Based Access Control
- Modern Responsive User Interface

---

# Technologies Used

## Backend
- Python
- Flask

## AI & Computer Vision
- OpenCV
- InsightFace
- YOLOv8
- EasyOCR
- NumPy
- SciPy

## Database
- MongoDB

## Frontend
- HTML
- CSS
- JavaScript

---

# System Modules

## 1. Authentication System
The platform includes a secure login system with OTP verification via email and role-based access control for officers, police administrators, and system administrators.

## 2. Facial Recognition Engine
ORYX uses InsightFace deep learning models to generate facial embeddings and perform real-time identity matching using cosine similarity comparison.

## 3. License Plate Recognition
The system uses YOLOv8 for license plate detection and EasyOCR for optical character recognition to identify vehicle plates from live video streams.

## 4. Officer Dashboard
The officer interface provides:
- Real-time alerts
- Live patrol monitoring
- Citizen management
- GPS tracking
- Incident logs
- Threat confirmation system

## 5. Admin Dashboard
The administrative dashboard allows:
- User management
- Role assignment
- Shift scheduling
- Monitoring officer activity
- Patrol supervision
- System log management

## 6. Police Monitoring Interface
The police interface includes:
- Live camera feeds
- Real-time face detection
- Wanted person identification
- Recognized persons list
- Plate detection system
- System alerts

---

# AI Models Used

## Face Recognition
- InsightFace (buffalo_l)

## Object Detection
- YOLOv8

## OCR
- EasyOCR

---

# Project Structure

```bash
ORYX/
│
├── static/
├── templates/
├── app.py
├── encode_and_seed.py
├── requirements.txt
```

---

# Installation

```bash
pip install flask opencv-python pymongo insightface ultralytics easyocr bcrypt flask-mail scipy numpy
```

---

# Run The Project

```bash
python app.py
```

---

# System Workflow

1. User logs into the system
2. OTP verification is sent via email
3. Officer accesses the dashboard
4. Live camera captures faces
5. AI model detects and recognizes identities
6. System classifies risk level
7. Alerts are generated instantly
8. Logs and patrol data are stored in MongoDB

---

# Current Status

Working Prototype / Live Demo Ready

The system currently supports:
- Real-time face recognition
- Live alerts
- GPS monitoring
- Multi-user dashboards
- License plate detection
- Incident logging

---

# Dataset Notice

Large datasets, training images, recorded videos, and AI model weights are excluded from this repository due to GitHub storage limitations and privacy considerations.

The ORYX system was trained and tested using custom facial recognition samples, security-related datasets, and real-time surveillance data prepared specifically for the project environment.

Some large files such as:
- Training datasets
- Recorded surveillance footage
- AI model weights (.pt)
- Image archives
- Video samples

are intentionally not included in the public repository.

The repository currently contains:
- Source code
- Web interface
- Backend system
- Frontend templates
- AI integration logic
- Database interaction modules
- System architecture implementation

A live working demonstration of the system is available during AI Expo Jordan 2026.

---

# Future Improvements

- Cloud deployment
- Edge AI optimization
- Mobile application integration
- Real-time analytics dashboard
- Advanced predictive threat analysis

