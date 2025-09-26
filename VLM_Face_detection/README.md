# 🎥 Live Webcam Detection and Streaming Server

A beginner-friendly real-time object, person, and face detection streaming system using:

- ✅ FastAPI backend
- ✅ OpenCV (laptop webcam)
- ✅ Ultralytics YOLOv8
- ✅ MySQL database
- ✅ Web UI with Play/Pause, Snapshot, Record, and Fullscreen buttons

---

## 🚀 Features

- Stream **Laptop Webcam** in any browser (Chrome, Edge, etc)
- Real-time **YOLOv8 face, person, and object detection**
- Save detection **snapshots to MySQL**
- Save full **video recordings to disk** (`/videos`)
- Intuitive Web UI served from `/`
- Toggle controls (single-click):  
  ▶ Play/Pause | 🖼 Snapshot ON/OFF | 💾 Record ON/OFF | ⛶ Fullscreen

---

## 🔧 Required Setup

### 📦 Prerequisites

- Python **3.8+**
- MySQL running (localhost)
- YOLOv8 `.pt` models (see below)
- Laptop or external webcam (OpenCV compatible)

---

### 📁 Folder Structure

your_project/
│
├─ main.py # FastAPI backend
├─ yolov8s-face.pt # YOLOv8 face detection model
├─ yolov8n.pt # YOLOv8 general detection model
├─ static/ # Web frontend
│ └─ index.html
├─ videos/ # Auto-created for recordings
├─ requirements.txt # Python dependencies
└─ README.md # This file


---

## ✅ Setup Instructions

### 1. 📥 Install Python Dependencies

pip install -r requirements.txt


### 2. 🛢️ Setup MySQL Database

Make sure MySQL is running.  
Create a database manually or via MySQL shell:

CREATE DATABASE db;


Edit `main.py` if your database user/password is different.

---

### 3. 📁 Add YOLOv8 Models

Download and place in the project root:
- ➤ [yolov8n.pt (object detection)](https://github.com/ultralytics/ultralytics/releases)
- ➤ [yolov8s-face.pt (face detection)](https://github.com/derronqi/yolov8-face)

---

## ▶️ Start the Server

uvicorn main:app --host 0.0.0.0 --port 8000


---

## 🌐 View in Browser

- Local machine:  
  `http://localhost:8000/`
- Other devices (same Wi-Fi):  
  `http://<your_ip>:8000/` (e.g., `http://192.168.1.24:8000/`)

---

## 🎮 Controls in UI

| Button              | Function                                      |
|---------------------|-----------------------------------------------|
| ▶ Play / ▶ Pause    | Toggle stream + detection on/off              |
| 🖼 Snapshot ON/OFF   | Enable/Disable saving snapshots in DB         |
| 💾 Record ON/OFF     | Enable/Disable saving recorded video clips    |
| ⛶ Fullscreen        | Toggle fullscreen video display                |
| 🔄 Refresh          | Restart the stream                            |

---

## 📂 Output Locations

| What                   | Location                          |
|------------------------|------------------------------------|
| Video recordings       | `/videos/stream_<timestamp>.mp4` |
| Snapshots (detections) | MySQL `detections` table          |
| Web UI (frontend)      | `static/index.html`               |

---


