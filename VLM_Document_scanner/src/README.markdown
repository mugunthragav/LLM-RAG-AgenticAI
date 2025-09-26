# Real-time Detection API with Notifications

## Overview
This project is a FastAPI-based application that provides real-time detection capabilities, including face recognition, general object detection, and person detection using the YOLOv8 model. It supports face registration for new employees and broadcasts detection results to connected clients via WebSocket. The system uses OpenCV, face_recognition, and Ultralytics YOLO for processing, and FastAPI for the API and WebSocket server. A separate WebSocket client script (`ws_listener.py`) is included to listen for notifications.

## Features
- **Face Recognition**: Identifies known faces in images using the `face_recognition` library.
- **Object Detection**: Detects objects in images using the YOLOv8 model.
- **Person Detection**: Filters YOLOv8 detections to identify only people.
- **Face Registration**: Allows registering new faces with employee names.
- **WebSocket Notifications**: Broadcasts detection results and registration events to connected clients.
- **API Documentation**: Interactive API docs available via FastAPI's Swagger UI.

## Prerequisites
- Python 3.8 or higher
- A system with `cmake` and a C++ compiler (required for `face_recognition` dependencies)
- A webcam or image source for testing (optional)
- A directory named `Training_images` containing `.jpg` images for face recognition training


2. **Create a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Training Images**:
   - Create a directory named `Training_images` in the project root.
   - Place `.jpg` images of faces in the `Training_images` directory, named as `<employee_name>.jpg`.

5. **Download YOLOv8 Model**:
   - The application uses the `yolov8n.pt` model, which is automatically downloaded by the `ultralytics` library when first used. Ensure internet access during the first run.

## Running the Application
1. **Start the FastAPI Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - The `--reload` flag enables auto-reload for development.
   - Access the API documentation at: `http://127.0.0.1:8000/docs`

2. **Start the WebSocket Client** (in a separate terminal):
   ```bash
   python ws_listener.py
   ```
   - This script connects to the WebSocket server and prints incoming notifications.

## API Endpoints
- **POST /detect/face**: Perform face recognition on an image. Expects a base64-encoded image.
- **POST /detect/object**: Perform general object detection using YOLOv8. Expects a base64-encoded image.
- **POST /detect/person**: Perform person detection using YOLOv8. Expects a base64-encoded image.
- **POST /register_face**: Register a new face with an employee name. Expects a base64-encoded image and employee name.
- **WebSocket /ws/notifications**: Connect to receive real-time detection and registration notifications.

## Example Usage
1. **Test Face Recognition**:
   Use the Swagger UI at `http://127.0.0.1:8000/docs` to send a base64-encoded image to the `/detect/face` endpoint.

2. **Register a New Face**:
   Send a POST request to `/register_face` with a JSON body:
   ```json
   {
       "image_base64": "<base64-encoded-image>",
       "employee_name": "JohnDoe"
   }
   ```

3. **Receive Notifications**:
   Run `ws_listener.py` to see real-time notifications for detections and registrations.

## Project Structure
```
project_root/
├── main.py              # FastAPI application with detection and WebSocket logic
├── ws_listener.py       # WebSocket client for receiving notifications
├── Training_images/     # Directory for storing face images (create this)
├── requirements.txt     # Python dependencies
├── README.md            # This file
```

## Dependencies
See `requirements.txt` for the full list of Python packages. Key dependencies include:
- `fastapi`: For the API and WebSocket server
- `opencv-python`: For image processing
- `face_recognition`: For face recognition
- `ultralytics`: For YOLOv8 object detection
- `websockets`: For the WebSocket client

