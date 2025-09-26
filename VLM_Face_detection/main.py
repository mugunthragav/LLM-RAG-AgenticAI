from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO
from dotenv import load_dotenv
import os
import cv2
import mysql.connector
from datetime import datetime
import numpy as np
import time
import shutil # Keep shutil for file copying

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configuration from env ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, os.getenv("VIDEO_DIR", "videos")) # Temporary recordings
DOWNLOAD_DIR = os.path.join(BASE_DIR, os.getenv("DOWNLOAD_DIR", "downloads")) # Permanent downloaded files (snapshots & videos)
SNAPSHOT_DIR = os.path.join(BASE_DIR, os.getenv("SNAPSHOT_DIR", "snapshots")) # Temporary snapshots (if not saved to downloads)

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True) # Ensure snapshot dir also exists

# Determine RTSP URL: if it's a digit, treat as camera index (e.g., 0 for webcam), otherwise as a string URL
rtsp_url = os.environ.get("RTSP_URL", "0") # Default to webcam 0 if not set
try:
    rtsp_url = int(rtsp_url)
except ValueError:
    pass # Keep as string if not an integer

camera_id = "main"

snapshot_enabled = False # For manual snapshot
record_enabled = False
detect_enabled = False   # Explicitly off by default
ui_state = {
    "playing": True,
    "latest_snapshot_id": None,
    "latest_video_id": None,
    "person_detected": False,
    "current_recording_path": None, # Renamed for clarity: this is the temporary file being written
    "detection_triggered": False,
    "last_detection_time": 0 # To prevent rapid re-triggering of detection snapshots/videos
}

# --- Models ---
face_model_path = os.getenv("FACE_MODEL_PATH", "yolov8s-face.pt")
object_model_path = os.getenv("OBJECT_MODEL_PATH", "yolov8n.pt")

face_model = YOLO(face_model_path)
object_model = YOLO(object_model_path)

# --- FastAPI App ---
app = FastAPI()

# --- Database Connection ---
db = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ref3")
)
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type VARCHAR(50),
        camera_id VARCHAR(50),
        snapshot_path VARCHAR(255), -- Path for saved snapshots
        video_path VARCHAR(255),    -- Path for saved videos
        snapshot LONGBLOB,          -- Raw snapshot bytes (optional, but keeping for consistency)
        video LONGBLOB,             -- Raw video bytes (optional, but keeping for consistency)
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
""")
db.commit()

def save_to_database(detection_type: str, camera_id: str, snapshot_filepath: str = None, video_filepath: str = None, snapshot_bytes: bytes = None, video_bytes: bytes = None):
    """
    Saves detection information to the database.
    Prioritizes file paths if available, also accepts raw bytes.
    """
    cursor.execute(
        "INSERT INTO detections (type, camera_id, snapshot_path, video_path, snapshot, video) VALUES (%s, %s, %s, %s, %s, %s)",
        (detection_type, camera_id, snapshot_filepath, video_filepath, snapshot_bytes, video_bytes)
    )
    db.commit()
    cursor.execute("SELECT LAST_INSERT_ID()")
    last_id = cursor.fetchone()[0]
    return last_id

# --- API Models ---
class SettingToggle(BaseModel):
    enable: bool

class PlayPauseRequest(BaseModel):
    action: str

@app.post("/ui/playpause")
def play_pause_control(request: PlayPauseRequest):
    action = request.action.lower()
    if action in ["play", "pause"]:
        ui_state["playing"] = (action == "play")
        print(f"[STATE] Play set to: {ui_state['playing']}")
        return {"playing": ui_state["playing"]}
    return {"error": "Invalid action"}

@app.post("/settings/snapshot")
def toggle_snapshot(setting: SettingToggle):
    global snapshot_enabled
    snapshot_enabled = setting.enable
    if snapshot_enabled:
        print("[ACTION] Manual snapshot requested.")
    # No need to return latest_snapshot_id immediately, it will be updated by generate_frames
    return {"snapshot_requested": snapshot_enabled}

@app.post("/settings/record")
def toggle_record(setting: SettingToggle):
    global record_enabled
    # If recording is being stopped
    if record_enabled and not setting.enable:
        print("[ACTION] Record stopped.")
        if ui_state["current_recording_path"] and os.path.exists(ui_state["current_recording_path"]):
            # Save the video that was just recorded
            video_id = save_recorded_video_to_db_and_disk(ui_state["current_recording_path"])
            ui_state["latest_video_id"] = video_id
            ui_state["current_recording_path"] = None # Reset temp path
            print(f"[INFO] Recording saved and processed with ID: {video_id}")
            record_enabled = setting.enable # Update state after saving
            return {"record_enabled": record_enabled, "video_id": video_id}
        else:
            print("[WARNING] No active recording path to save.")
            record_enabled = setting.enable # Update state even if nothing to save
            return {"record_enabled": record_enabled, "video_id": None}
    
    # If recording is being started or remains off
    record_enabled = setting.enable
    print(f"[STATE] Record: {'ON' if record_enabled else 'OFF'}")
    return {"record_enabled": record_enabled, "video_id": ui_state["latest_video_id"] if not record_enabled else None}


def save_snapshot(annotated_frame, detection_type):
    global ui_state
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save to downloads directory for persistent access
    snapshot_filepath = os.path.join(DOWNLOAD_DIR, f"{camera_id}_{detection_type}_{timestamp}.jpg")
    cv2.imwrite(snapshot_filepath, annotated_frame)
    
    success, encoded = cv2.imencode(".jpg", annotated_frame)
    if success:
        snapshot_id = save_to_database(detection_type, camera_id, snapshot_filepath, None, encoded.tobytes())
        ui_state["latest_snapshot_id"] = snapshot_id
        print(f"[INFO] Snapshot saved to DB and disk with ID: {snapshot_id} at {snapshot_filepath}")
    else:
        print(f"[ERROR] Failed to encode snapshot for DB storage for type {detection_type}.")
        snapshot_id = None
    return snapshot_id

def save_recorded_video_to_db_and_disk(temp_video_path):
    global ui_state
    video_id = None
    if os.path.exists(temp_video_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine the final download path based on the temporary file's extension
        # Since we are forcing .avi, we can hardcode it here or use os.path.splitext
        download_filepath = os.path.join(DOWNLOAD_DIR, f"{camera_id}_recording_{timestamp}.avi")
        
        try:
            # Simply copy the AVI file to the download directory
            shutil.copy(temp_video_path, download_filepath)
            print(f"[INFO] Video copied to permanent download location: {download_filepath}")

            # No need to read video_bytes if you're primarily storing the path
            video_id = save_to_database("video_recording", camera_id, None, download_filepath, None, None)
            ui_state["latest_video_id"] = video_id
            print(f"[INFO] Video saved to DB with ID: {video_id} and path: {download_filepath}")
            
        except Exception as e:
            print(f"[ERROR] Failed to copy/save video: {e}")
        finally:
            try:
                # Always remove the temporary recording file
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                    print(f"[INFO] Temporary video file {temp_video_path} deleted successfully")
            except PermissionError as e:
                print(f"[ERROR] Failed to delete temporary video file: {e}")
            except Exception as e:
                print(f"[ERROR] An unexpected error occurred while deleting temporary file: {e}")
    else:
        print(f"[WARNING] Temporary video path {temp_video_path} does not exist for saving.")
    
    ui_state["current_recording_path"] = None # Ensure it's cleared after processing
    return video_id

@app.post("/settings/detections")
def toggle_detections(setting: SettingToggle):
    global detect_enabled
    detect_enabled = setting.enable
    ui_state["detection_triggered"] = False  # Reset detection trigger when toggling
    ui_state["last_detection_time"] = 0 # Reset last detection time
    print(f"[STATE] Detections: {'ON' if detect_enabled else 'OFF'}")
    return {"detect_enabled": detect_enabled}

def generate_frames():
    global snapshot_enabled, record_enabled, detect_enabled, ui_state
    cap = None
    writer = None
    
    # Force MJPG codec and AVI container for all temporary and permanent recordings
    # This is highly compatible with most OpenCV builds
    video_codec = cv2.VideoWriter_fourcc(*'MJPG') 
    video_ext = '.avi'
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            print(f"[ERROR] Failed to open stream from {rtsp_url}. Please check the URL and camera availability.")
            # Yield an error frame or message to the client
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Stream Offline", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode(".jpg", error_frame)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   buffer.tobytes() + b"\r\n")
            return

        print("[INFO] Stream started.")
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: # Handle cases where FPS might not be reported correctly
            fps = 15
            print(f"[WARNING] FPS not reported, defaulting to {fps}.")
        
        # Min time between detection-triggered actions (e.g., 5 seconds)
        DETECTION_COOLDOWN = 5 

        while True:
            if not ui_state["playing"]:
                # If paused, still read a frame to keep the stream alive (if possible)
                cap.grab() # Use grab() to discard frame but keep buffer clear
                cv2.waitKey(100) # Give CPU a break
                continue

            ret, frame = cap.read()
            if not ret:
                print("[WARNING] Empty frame received or stream ended. Reconnecting in 5 seconds...")
                if cap:
                    cap.release()
                time.sleep(5) # Wait before attempting to reconnect
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    print("[FATAL] Failed to reconnect stream.")
                    break # Exit the loop if reconnection fails
                continue

            # --- CRITICAL FIX: Ensure 'annotated' is always defined ---
            annotated = frame.copy() 
            has_person_or_face = False

            if detect_enabled:
                # Check for empty frames before passing to YOLO
                if frame is None or frame.size == 0:
                    print("[WARNING] Received empty frame, skipping detection.")
                    continue # Skip current frame, try next
                    
                face_results = face_model(frame, verbose=False) # Suppress YOLO output for cleaner console
                face_boxes = face_results[0].boxes if face_results and len(face_results) > 0 else []
                has_face = len(face_boxes) > 0
                for box in face_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 50, 150), 2)
                    cv2.putText(annotated, f"Face {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 50, 150), 2)

                object_results = object_model(frame, verbose=False) # Suppress YOLO output
                object_boxes = object_results[0].boxes if object_results and len(object_results) > 0 else []
                object_labels = []
                for box in object_boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    label = object_model.names[cls]
                    conf = float(box.conf[0])
                    object_labels.append(label)
                    color = (0, 255, 0) if label == "person" else (0, 165, 255)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                has_person = "person" in object_labels
                has_person_or_face = has_person or has_face # Trigger if either person or face is detected
                
                # Update UI state for frontend to show detection status
                ui_state["person_detected"] = has_person_or_face 
                
                current_time = time.time()
                # Trigger snapshot/video on detection if not already triggered and cooldown passed
                if has_person_or_face and not ui_state["detection_triggered"] and \
                   (current_time - ui_state["last_detection_time"] > DETECTION_COOLDOWN):
                    snapshot_id = save_snapshot(annotated, "detection_trigger")
                    ui_state["latest_snapshot_id"] = snapshot_id
                    ui_state["detection_triggered"] = True # Set flag to prevent immediate re-trigger
                    ui_state["last_detection_time"] = current_time
                    print(f"[INFO] Detection triggered snapshot saved with ID: {snapshot_id}")
                elif not has_person_or_face:
                    # Reset detection trigger if no person/face is detected after some time
                    # This allows re-triggering if person leaves and re-enters
                    ui_state["detection_triggered"] = False


            else: # If detections are disabled
                ui_state["person_detected"] = False
                ui_state["detection_triggered"] = False
                ui_state["last_detection_time"] = 0

            # Manual snapshot
            if snapshot_enabled:
                snapshot_id = save_snapshot(annotated, "manual")
                ui_state["latest_snapshot_id"] = snapshot_id
                snapshot_enabled = False # Reset immediately after taking one snapshot

            # Recording logic
            if record_enabled and not writer:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Store in VIDEO_DIR temporarily during recording as AVI with MJPG
                temp_video_path = os.path.join(VIDEO_DIR, f"{camera_id}_recording_temp_{timestamp}{video_ext}")
                
                writer = cv2.VideoWriter(temp_video_path, video_codec, fps, (w, h))

                if not writer.isOpened():
                    print(f"[ERROR] Failed to initialize VideoWriter with codec {video_codec} for {video_ext}. Recording disabled.")
                    record_enabled = False # Turn off recording if writer fails
                    ui_state["current_recording_path"] = None
                    writer = None # Ensure writer is None if failed
                else:
                    ui_state["current_recording_path"] = temp_video_path
                    print(f"[DEBUG] VideoWriter initialized with MJPG at {temp_video_path}")

            if record_enabled and writer and writer.isOpened():
                writer.write(annotated)
            elif not record_enabled and writer: # If recording was enabled but now turned off
                writer.release()
                print("[INFO] VideoWriter released due to recording being stopped.")
                # The save_recorded_video_to_db_and_disk is now called from toggle_record endpoint.
                writer = None # Reset writer
                
            success, buffer = cv2.imencode(".jpg", annotated)
            if success:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" +
                       buffer.tobytes() + b"\r\n")
            else:
                print("[ERROR] Failed to encode frame to JPEG.")
                
    except Exception as e:
        print(f"[FATAL] Stream generation crashed: {e}")
    finally:
        if cap:
            cap.release()
            print("[INFO] Camera released.")
        if writer:
            writer.release()
            print("[INFO] VideoWriter released during stream shutdown.")
            # If the stream crashes while recording, attempt to save the partial video
            if ui_state["current_recording_path"] and os.path.exists(ui_state["current_recording_path"]):
                print("[INFO] Attempting to save current partial recording due to stream shutdown.")
                # Pass the current_recording_path, not video_path
                save_recorded_video_to_db_and_disk(ui_state["current_recording_path"]) 
        print("[INFO] Stream process ended.")

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/download/snapshot/{snapshot_id}")
def download_snapshot(snapshot_id: int):
    # Retrieve the snapshot's file path from the database first
    cursor.execute("SELECT snapshot_path FROM detections WHERE id = %s", (snapshot_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        # Fallback: if path is not found, try to retrieve from BLOB directly
        cursor.execute("SELECT snapshot FROM detections WHERE id = %s", (snapshot_id,))
        blob_result = cursor.fetchone()
        if blob_result and blob_result[0]:
            print(f"[WARNING] Snapshot path not found for ID {snapshot_id}, serving from BLOB.")
            return Response(content=blob_result[0], media_type="image/jpeg",
                            headers={"Content-Disposition": f"attachment; filename=snapshot_{snapshot_id}.jpg"})
        else:
            raise HTTPException(status_code=404, detail="Snapshot not found")

    snapshot_filepath = result[0]
    if not os.path.exists(snapshot_filepath):
        print(f"[ERROR] Snapshot file not found on disk: {snapshot_filepath}. Attempting to serve from BLOB if available.")
        # Fallback to BLOB if file not found on disk
        cursor.execute("SELECT snapshot FROM detections WHERE id = %s", (snapshot_id,))
        blob_result = cursor.fetchone()
        if blob_result and blob_result[0]:
            return Response(content=blob_result[0], media_type="image/jpeg",
                            headers={"Content-Disposition": f"attachment; filename=snapshot_{snapshot_id}.jpg"})
        else:
            raise HTTPException(status_code=404, detail="Snapshot file not found on disk and no BLOB data.")

    # Serve the file directly from the filesystem
    with open(snapshot_filepath, "rb") as f:
        snapshot_bytes = f.read()
    
    return Response(content=snapshot_bytes, media_type="image/jpeg",
                    headers={"Content-Disposition": f"attachment; filename={os.path.basename(snapshot_filepath)}"})

@app.get("/download/video/{video_id}")
def download_video(video_id: int):
    # Retrieve the video's file path from the database first
    cursor.execute("SELECT video_path FROM detections WHERE id = %s", (video_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        # Fallback: if path is not found, try to retrieve from BLOB directly
        cursor.execute("SELECT video FROM detections WHERE id = %s", (video_id,))
        blob_result = cursor.fetchone()
        if blob_result and blob_result[0]:
            print(f"[WARNING] Video path not found for ID {video_id}, serving from BLOB. File extension might be generic.")
            return Response(content=blob_result[0], media_type="video/x-msvideo", # Set to AVI
                            headers={"Content-Disposition": f"attachment; filename=video_{video_id}.avi"}) # Set to AVI
        else:
            raise HTTPException(status_code=404, detail="Video not found")

    video_filepath = result[0]
    if not os.path.exists(video_filepath):
        print(f"[ERROR] Video file not found on disk: {video_filepath}. Attempting to serve from BLOB if available.")
        # Fallback to BLOB if file not found on disk
        cursor.execute("SELECT video FROM detections WHERE id = %s", (video_id,))
        blob_result = cursor.fetchone()
        if blob_result and blob_result[0]:
            return Response(content=blob_result[0], media_type="video/x-msvideo", # Set to AVI
                            headers={"Content-Disposition": f"attachment; filename=video_{video_id}.avi"}) # Set to AVI
        else:
            raise HTTPException(status_code=404, detail="Video file not found on disk and no BLOB data.")

    # Determine media type based on file extension
    media_type = "application/octet-stream" # Default
    if video_filepath.endswith(".avi"):
        media_type = "video/x-msvideo"
    # No .mp4 logic needed if we only record AVI

    # Serve the file directly from the filesystem
    with open(video_filepath, "rb") as f:
        video_bytes = f.read()
    
    return Response(content=video_bytes, media_type=media_type,
                    headers={"Content-Disposition": f"attachment; filename={os.path.basename(video_filepath)}"})

@app.get("/api/camera_status")
def get_camera_status():
    return {
        "playing": ui_state["playing"],
        "latest_snapshot_id": ui_state["latest_snapshot_id"],
        "latest_video_id": ui_state["latest_video_id"],
        "person_detected": ui_state["person_detected"], # Added to reflect current detection status
        "record_enabled": record_enabled, # Added to reflect current recording status
        "detect_enabled": detect_enabled # Added to reflect current detection status
    }

app.mount("/", StaticFiles(directory="static", html=True), name="static")