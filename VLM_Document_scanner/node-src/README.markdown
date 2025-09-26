# IP Camera Streaming Server

This project sets up a Node.js server to stream video from an IP camera using RTSP, converting it to an HLS (HTTP Live Streaming) format for web playback.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Prerequisites
- **Node.js**: Version 14 or higher
- **FFmpeg**: Installed and accessible via command line
- **IP Camera**: Configured with an accessible RTSP stream URL
- **Network Access**: Ensure the server and client devices are on the same network


1. Install dependencies:
   ```bash
   npm install
   ```
2. Install FFmpeg:
   - On Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH.
   - On macOS: `brew install ffmpeg`
   - On Linux: `sudo apt-get install ffmpeg` (Ubuntu/Debian) or equivalent for your distribution.
3. Ensure the `ffmpeg-static` package is correctly installed:
   ```bash
   npm install ffmpeg-static
   ```

## Configuration
1. Open `server.js` and update the `rtspUrl` with your IP camera's RTSP stream URL:
   ```javascript
   const rtspUrl = 'rtsp://<username>:<password>@<camera-ip>:<port>/stream1';
   ```
   - Replace `<username>`, `<password>`, `<camera-ip>`, and `<port>` with your camera's credentials and network details.
2. Ensure the server IP in `server.js` matches your machine’s IP:
   ```javascript
   console.log(`Server running at http://192.168.1.35:${port}`);
   ```
   - Update `192.168.1.35` to your server’s IP if different.

## Usage
1. Start the server:
   ```bash
   node server.js
   ```
2. Access the webpage:
   - Open a browser and navigate to `http://<server-ip>:3000` (e.g., `http://192.168.1.35:3000`).
3. View the stream:
   - The HLS stream is available at `http://<server-ip>:3000/videos/ipcam/index.m3u8`.
   - If `index.html` is configured with a video player, it will load the stream automatically.

## Project Structure
```
├── index.html        # Webpage for viewing the stream (currently empty)
├── server.js         # Node.js server handling RTSP to HLS conversion
├── videos/           # Directory for storing HLS segments
│   └── ipcam/        # Subdirectory for IP camera stream files
├── node_modules/     # Node.js dependencies
├── package.json      # Project metadata and dependencies
└── README.md         # Project documentation
```
