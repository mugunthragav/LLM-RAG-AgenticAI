import cv2
import numpy as np
import face_recognition
import os
from ultralytics import YOLO
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import base64
import json
from typing import List
import logging
from datetime import datetime
import mysql.connector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration and Initialization ---

TRAINING_IMAGES_PATH = 'Training_images'
RECORDINGS_PATH = 'Recordings'
SNAPSHOTS_PATH = 'Snapshots' # Keeping this for consistency, though local save is removed

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',     # Replace with your MySQL username
    'password': 'smackie.1017', # Replace with your MySQL password
    'database': 'security_system'
}

class AppState:
    def __init__(self):
        self.encode_list_known = []
        self.class_names = []
        self.yolo_model = None
        self.processing_lock = asyncio.Lock()
        self.websocket_clients: List[WebSocket] = []
        self.recording_process = None   # Track recording state
        self.recording_filename = None
        self.db_connection = None # Add DB connection to app state

app_state = AppState()
app = FastAPI(
    title="Real-time Detection API with Notifications",
    description="API for Face Recognition, Object Detection, Person Detection, Face Registration, Recording, Snapshots, and WebSocket Notifications.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models for API Requests/Responses ---

class ImageRequest(BaseModel):
    image_base64: str

class RegisterFaceRequest(BaseModel):
    image_base64: str
    employee_name: str

class RecordRequest(BaseModel):
    action: str   # 'start' or 'stop'
    source: str   # RTSP URL or camera index

class SnapshotRequest(BaseModel):
    source: str   # 'provided' for base664 image
    image_base64: str
    detection_type: str = None # Add new field, make it optional for backward compatibility

# --- Face Recognition Setup ---

def load_and_encode_faces(path):
    images = []
    class_names = []
    if not os.path.exists(path):
        logger.info(f"Training images path not found: {path}. Creating it.")
        os.makedirs(path)
        return [], []

    myList = os.listdir(path)
    logger.info(f"Found files in Training_images: {myList}")

    for cl in myList:
        img_path = os.path.join(path, cl)
        curImg = cv2.imread(img_path)
        if curImg is not None:
            images.append(curImg)
            class_names.append(os.path.splitext(cl)[0])
        else:
            logger.warning(f"Could not read image: {img_path}")
    logger.info(f"Loaded face class names: {class_names}")

    encodeList = []
    for img in images:
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(img_rgb)
            if face_locations:
                encode = face_recognition.face_encodings(img_rgb, face_locations)[0]
                encodeList.append(encode)
            else:
                logger.warning("No face found in one of the training images.")
        except Exception as e:
            logger.error(f"Error encoding an image: {e}")
    return encodeList, class_names

async def reload_face_encodings():
    logger.info("Reloading face encodings...")
    app_state.encode_list_known, app_state.class_names = await asyncio.to_thread(load_and_encode_faces, TRAINING_IMAGES_PATH)
    logger.info("Face Encodings Reload Complete.")

# --- WebSocket Broadcasting ---

async def broadcast_notification(message: dict):
    disconnected_clients = []
    for client in app_state.websocket_clients:
        try:
            await client.send_json(message)
        except WebSocketDisconnect:
            disconnected_clients.append(client)
        except Exception as e:
            logger.error(f"Error sending WebSocket message to client: {e}")
            disconnected_clients.append(client)

    for client in disconnected_clients:
        if client in app_state.websocket_clients:
            app_state.websocket_clients.remove(client)

# --- Database Operations ---
async def connect_db():
    try:
        app_state.db_connection = mysql.connector.connect(**DB_CONFIG)
        logger.info("Connected to MySQL database!")
    except mysql.connector.Error as err:
        logger.error(f"Error connecting to MySQL: {err}")
        app_state.db_connection = None

async def close_db():
    if app_state.db_connection and app_state.db_connection.is_connected():
        app_state.db_connection.close()
        logger.info("MySQL connection closed.")

async def insert_snapshot_to_db(filename: str, image_bytes: bytes, detection_type: str = None): # Added detection_type
    if not app_state.db_connection or not app_state.db_connection.is_connected():
        await connect_db()
        if not app_state.db_connection or not app_state.db_connection.is_connected():
            logger.error("Failed to connect to database for snapshot insertion.")
            return

    try:
        cursor = app_state.db_connection.cursor()
        # Modified SQL to include detection_type
        sql = "INSERT INTO snapshots (filename, image_data, detection_type) VALUES (%s, %s, %s)"
        cursor.execute(sql, (filename, image_bytes, detection_type)) # Pass detection_type
        app_state.db_connection.commit()
        logger.info(f"Snapshot '{filename}' with type '{detection_type}' saved to database.")
    except mysql.connector.Error as err:
        logger.error(f"Error saving snapshot to database: {err}")
        app_state.db_connection.rollback() # Rollback on error
    finally:
        if cursor:
            cursor.close()


# --- FastAPI Event Handlers ---

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up API...")
    await reload_face_encodings()
    try:
        app_state.yolo_model = YOLO('yolov8n.pt')
        logger.info("YOLOv8 model loaded.")
    except Exception as e:
        logger.error(f"Error loading YOLO model: {e}")
    # Create directories for recordings and snapshots
    for path in [RECORDINGS_PATH, SNAPSHOTS_PATH]:
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created directory: {path}")
        else:
            logger.info(f"Directory exists: {path}")
    await connect_db() # Connect to DB on startup

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")
    await close_db() # Close DB connection on shutdown

# --- Helper Functions ---

def decode_image(base64_string):
    try:
        img_bytes = base64.b64decode(base64_string)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from base64 string.")
        return img
    except Exception as e:
        raise ValueError(f"Error decoding base64 image: {e}")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Detection API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "yolo_model_loaded": app_state.yolo_model is not None,
        "face_encodings_count": len(app_state.encode_list_known),
        "known_faces": app_state.class_names,
        "recording_active": app_state.recording_process is not None,
        "database_connected": app_state.db_connection is not None and app_state.db_connection.is_connected()
    }

@app.post("/detect/face", summary="Perform face recognition on an image")
async def detect_face(request: ImageRequest):
    try:
        img = decode_image(request.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data.")
        
        loop = asyncio.get_event_loop()
        face_results = await loop.run_in_executor(None, lambda: _process_face_detection(img))
        
        if face_results["faces"]:
            notification = {
                "type": "face_detection",
                "timestamp": asyncio.get_event_loop().time(),
                "data": face_results["faces"]
            }
            await broadcast_notification(notification)
        
        return JSONResponse(content=face_results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during face detection: {e}")
        raise HTTPException(status_code=500, detail=f"Error during face detection: {e}")

def _process_face_detection(img):
    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
    facesCurFrame = face_recognition.face_locations(imgS)
    encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
    detected_faces = []
    
    for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
        matches = face_recognition.compare_faces(app_state.encode_list_known, encodeFace)
        faceDis = face_recognition.face_distance(app_state.encode_list_known, encodeFace)
        
        name = "Unknown"
        confidence = 0.0
        
        if len(faceDis) > 0:
            matchIndex = np.argmin(faceDis)
            confidence = 1 - faceDis[matchIndex]
            if matches[matchIndex] and confidence > 0:
                name = app_state.class_names[matchIndex].upper()
        
        y1, x2, y2, x1 = faceLoc
        y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
        detected_faces.append({
            "name": name,
            "bounding_box": [x1, y1, x2, y2],
            "confidence": float(f"{confidence:.2f}")
        })
    
    return {"faces": detected_faces}

@app.post("/detect/object", summary="Perform general object detection on an image")
async def detect_object(request: ImageRequest):
    try:
        img = decode_image(request.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data.")
        if app_state.yolo_model is None:
            raise HTTPException(status_code=503, detail="YOLO model not loaded.")
        
        loop = asyncio.get_event_loop()
        object_results = await loop.run_in_executor(None, lambda: _process_object_detection(img, filter_person=False))
        
        if object_results["detections"]:
            notification = {
                "type": "object_detection",
                "timestamp": asyncio.get_event_loop().time(),
                "data": object_results["detections"]
            }
            await broadcast_notification(notification)
        
        return JSONResponse(content=object_results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during object detection: {e}")
        raise HTTPException(status_code=500, detail=f"Error during object detection: {e}")

@app.post("/detect/person", summary="Perform person detection on an image")
async def detect_person(request: ImageRequest):
    try:
        img = decode_image(request.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data.")
        if app_state.yolo_model is None:
            raise HTTPException(status_code=503, detail="YOLO model not loaded.")
        
        loop = asyncio.get_event_loop()
        person_results = await loop.run_in_executor(None, lambda: _process_object_detection(img, filter_person=True))
        
        if person_results["detections"]:
            notification = {
                "type": "person_detection",
                "timestamp": asyncio.get_event_loop().time(),
                "data": person_results["detections"]
            }
            await broadcast_notification(notification)
        
        return JSONResponse(content=person_results)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during person detection: {e}")
        raise HTTPException(status_code=500, detail=f"Error during person detection: {e}")

def _process_object_detection(img, filter_person=False):
    results = app_state.yolo_model(img, verbose=False)
    detected_objects = []
    
    for r in results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = box.conf[0]
                cls = int(box.cls[0])
                label = app_state.yolo_model.names[cls]
                
                if filter_person and cls != 0:   # 0 is person class in COCO
                    continue
                
                detected_objects.append({
                    "label": label,
                    "confidence": float(f"{conf:.2f}"),
                    "bounding_box": [x1, y1, x2, y2]
                })
    
    return {"detections": detected_objects}

@app.post("/register_face", summary="Register a new face for recognition")
async def register_face(request: RegisterFaceRequest):
    try:
        img = decode_image(request.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data.")
        
        employee_name = request.employee_name.strip()
        if not employee_name:
            raise HTTPException(status_code=400, detail="Employee name cannot be empty.")
        
        if not os.path.exists(TRAINING_IMAGES_PATH):
            os.makedirs(TRAINING_IMAGES_PATH)
        
        save_path = os.path.join(TRAINING_IMAGES_PATH, f"{employee_name}.jpg")
        cv2.imwrite(save_path, img)
        
        await reload_face_encodings()
        
        notification = {
            "type": "face_registration",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {"name": employee_name, "file": save_path}
        }
        await broadcast_notification(notification)
        
        return JSONResponse(content={
            "status": "Face registered successfully", 
            "name": employee_name, 
            "file": save_path
        })
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during face registration: {e}")
        raise HTTPException(status_code=500, detail=f"Error during face registration: {e}")

@app.post("/record", summary="Start or stop recording from a source")
async def record(request: RecordRequest):
    try:
        action = request.action.lower()
        source = request.source
        logger.info(f"Record request: action={action}, source={source}")

        if action not in ['start', 'stop']:
            raise HTTPException(status_code=400, detail="Action must be 'start' or 'stop'")

        async with app_state.processing_lock:
            if action == 'start':
                if app_state.recording_process is not None:
                    raise HTTPException(status_code=400, detail="Recording is already in progress")

                # Generate unique filename based on timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                app_state.recording_filename = os.path.join(RECORDINGS_PATH, f"recording_{timestamp}.mp4")
                
                # Open video capture
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    raise HTTPException(status_code=500, detail=f"Failed to open source: {source}")

                # Get video properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30

                # Initialize video writer
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(app_state.recording_filename, fourcc, fps, (width, height))

                # Start recording in a separate task
                async def record_task():
                    try:
                        while app_state.recording_process:
                            ret, frame = cap.read()
                            if not ret:
                                logger.error("Failed to read frame from source")
                                break
                            out.write(frame)
                            await asyncio.sleep(0)  # Yield control
                    except Exception as e:
                        logger.error(f"Recording error: {e}")
                    finally:
                        cap.release()
                        out.release()
                        app_state.recording_process = None
                        app_state.recording_filename = None
                        logger.info("Recording stopped")

                app_state.recording_process = asyncio.create_task(record_task())
                logger.info(f"Started recording to {app_state.recording_filename}")

                notification = {
                    "type": "recording_started",
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {"filename": app_state.recording_filename}
                }
                await broadcast_notification(notification)
                return JSONResponse(content={"status": "Recording started", "filename": app_state.recording_filename})

            elif action == 'stop':
                if app_state.recording_process is None:
                    raise HTTPException(status_code=400, detail="No recording in progress")

                app_state.recording_process.cancel()
                app_state.recording_process = None
                filename = app_state.recording_filename
                app_state.recording_filename = None

                notification = {
                    "type": "recording_stopped",
                    "timestamp": asyncio.get_event_loop().time(),
                    "data": {"filename": filename}
                }
                await broadcast_notification(notification)
                return JSONResponse(content={"status": "Recording stopped", "filename": filename})

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during recording: {e}")
        raise HTTPException(status_code=500, detail=f"Error during recording: {e}")

@app.post("/snapshot", summary="Capture a snapshot from a source")
async def snapshot(request: SnapshotRequest):
    try:
        if request.source != 'provided':
            raise HTTPException(status_code=400, detail="Only 'provided' source is supported for snapshots")

        img = decode_image(request.image_base64)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Generate unique filename based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"snapshot_{timestamp}.jpg" # Just the filename for DB

        # Convert image to bytes for storage
        _, img_encoded = cv2.imencode('.jpg', img)
        image_bytes = img_encoded.tobytes()

        # Save snapshot to database (This line remains)
        await insert_snapshot_to_db(snapshot_filename, image_bytes, request.detection_type)

        # Removed: code to save snapshot to local file system

        notification = {
            "type": "snapshot_captured",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {"filename": snapshot_filename, "detection_type": request.detection_type} # Send filename and detection type as stored in DB
        }
        await broadcast_notification(notification)

        return JSONResponse(content={"status": "Snapshot captured", "filename": snapshot_filename, "detection_type": request.detection_type})

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Error during snapshot: {e}")

@app.get("/snapshots/{snapshot_id}", summary="Retrieve a snapshot by ID from the database")
async def get_snapshot(snapshot_id: int):
    logger.info(f"Received request for snapshot ID: {snapshot_id}")
    if not app_state.db_connection or not app_state.db_connection.is_connected():
        logger.warning("Database connection not active for snapshot retrieval. Attempting to reconnect...")
        await connect_db()
        if not app_state.db_connection or not app_state.db_connection.is_connected():
            logger.error("Failed to establish database connection for snapshot retrieval.")
            raise HTTPException(status_code=500, detail="Database not connected. Please check server logs.")

    try:
        cursor = app_state.db_connection.cursor()
        sql = "SELECT image_data FROM snapshots WHERE id = %s"
        cursor.execute(sql, (snapshot_id,))
        result = cursor.fetchone()

        if result:
            image_data = result[0]
            logger.info(f"Snapshot ID {snapshot_id} found. Sending image.")
            # Return the image data with the correct media type
            return Response(content=image_data, media_type="image/jpeg")
        else:
            logger.warning(f"Snapshot with ID {snapshot_id} not found in database.")
            raise HTTPException(status_code=404, detail="Snapshot not found.")
    except mysql.connector.Error as err:
        logger.error(f"MySQL error retrieving snapshot {snapshot_id}: {err}")
        raise HTTPException(status_code=500, detail=f"Error retrieving snapshot from database: {err}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving snapshot {snapshot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    finally:
        if cursor:
            cursor.close()

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    app_state.websocket_clients.append(websocket)
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")
    except WebSocketDisconnect:
        app_state.websocket_clients.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        app_state.websocket_clients.remove(websocket)
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Detection API Server...")
    print("Access API documentation at: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)