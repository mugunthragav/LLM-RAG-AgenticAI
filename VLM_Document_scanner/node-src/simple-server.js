const express = require('express');
const cors = require('cors');
const path = require('path');
const axios = require('axios');
const { spawn } = require('child_process');
const fs = require('fs');
const nodemailer = require('nodemailer');

const app = express();
const port = 3000;

// Configuration
const DETECTION_API_URL = 'http://127.0.0.1:8000';
const RTSP_URL = 'rtsp://mugunth:rasa1234@192.168.1.5:554/stream1';
const HLS_OUTPUT_DIR = path.join(__dirname, 'videos', 'ipcam');
const HLS_PLAYLIST = path.join(HLS_OUTPUT_DIR, 'index.m3u8');

// Email configuration
const EMAIL_CONFIG = {
    service: 'gmail',
    auth: {
        user: 'sy19251017@gmail.com', // Replace with your email
        pass: 'ignt dsdx buvr hadi' // Replace with your app-specific password
    },
    recipient_emails: ['sy19251017@gmail.com', 'sy19251017@gmail.com'] // Replace with recipient emails
};

// Create nodemailer transporter
const transporter = nodemailer.createTransport({
    service: EMAIL_CONFIG.service,
    auth: EMAIL_CONFIG.auth
});

let ffmpegProcess = null;
let isRecordingEnabled = false;
let isSnapshotEnabled = false;

// Middleware
app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use('/videos', express.static(path.join(__dirname, 'videos')));

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'compact_monitor.html'));
});

app.get('/stream', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Modified /api/detect/:type to handle 'object' as well
app.post('/api/detect/:type', async (req, res) => {
    try {
        const { type } = req.params;
        if (!req.body.image_base64) {
            return res.status(400).json({ error: 'Missing image_base64' });
        }

        console.log(`Starting detection for type: ${type}`);
        const response = await axios.post(`${DETECTION_API_URL}/detect/${type}`, req.body, {
            timeout: 15000
        });

        // Trigger recording or snapshot if enabled and detections are found
        const results = response.data;
        // Adjust hasDetections logic to check the correct key based on type
        let hasDetections = false;
        if (type === 'face') {
            hasDetections = results.faces && results.faces.length > 0;
        } else if (type === 'person' || type === 'object') {
            hasDetections = results.detections && results.detections.length > 0;
        }

        if (hasDetections) {
            // Send email notification
            const subject = `${type.charAt(0).toUpperCase() + type.slice(1)} Detection Alert`;
            let bodyContent;
            if (type === 'face') {
                bodyContent = results.faces;
            } else if (type === 'person' || type === 'object') {
                bodyContent = results.detections;
            }
            const body = `Detection event:\n\n${JSON.stringify(bodyContent, null, 2)}`;
            await sendEmailNotification(subject, body);

            if (isRecordingEnabled) {
                console.log('Triggering recording start');
                await axios.post(`${DETECTION_API_URL}/record`, {
                    action: 'start',
                    source: RTSP_URL
                }, { timeout: 5000 }).catch(err => {
                    console.error(`Failed to start recording: ${err.message}`);
                });
            }
            if (isSnapshotEnabled) {
                console.log('Triggering snapshot');
                await axios.post(`${DETECTION_API_URL}/snapshot`, {
                    source: 'provided',
                    image_base64: req.body.image_base64
                }, { timeout: 5000 }).catch(err => {
                    console.error(`Failed to capture snapshot: ${err.message}`);
                });
            }
        }

        res.json(response.data);
    } catch (error) {
        console.error(`Detection error for ${type}: ${error.message}`);
        res.status(500).json({ error: 'Detection service unavailable' });
    }
});

app.get('/api/status', (req, res) => {
    res.json({
        streaming: fs.existsSync(HLS_PLAYLIST),
        timestamp: new Date().toISOString(),
        recording_enabled: isRecordingEnabled,
        snapshot_enabled: isSnapshotEnabled,
        ffmpeg_running: !!ffmpegProcess
    });
});

app.post('/api/record/toggle', async (req, res) => {
    try {
        isRecordingEnabled = !isRecordingEnabled;
        console.log(`Toggling recording: ${isRecordingEnabled ? 'ON' : 'OFF'}`);
        if (!isRecordingEnabled) {
            console.log('Stopping recording');
            await axios.post(`${DETECTION_API_URL}/record`, { action: 'stop', source: RTSP_URL }, { timeout: 5000 });
        }
        // Send email notification
        const subject = `Recording ${isRecordingEnabled ? 'Enabled' : 'Disabled'} Alert`;
        const body = `Recording has been ${isRecordingEnabled ? 'enabled' : 'disabled'}.`;
        await sendEmailNotification(subject, body);
        res.json({ recording_enabled: isRecordingEnabled });
    } catch (error) {
        console.error(`Record toggle error: ${error.message}`);
        res.status(500).json({ error: 'Failed to toggle recording' });
    }
});

app.post('/api/snapshot/toggle', async (req, res) => {
    try {
        isSnapshotEnabled = !isSnapshotEnabled;
        console.log(`Toggling snapshot: ${isSnapshotEnabled ? 'ON' : 'OFF'}`);
        // Send email notification
        const subject = `Snapshot ${isSnapshotEnabled ? 'Enabled' : 'Disabled'} Alert`;
        const body = `Snapshot capture has been ${isSnapshotEnabled ? 'enabled' : 'disabled'}.`;
        await sendEmailNotification(subject, body);
        res.json({ snapshot_enabled: isSnapshotEnabled });
    } catch (error) {
        console.error(`Snapshot toggle error: ${error.message}`);
        res.status(500).json({ error: 'Failed to toggle snapshot' });
    }
});

// Email notification function
async function sendEmailNotification(subject, body) {
    try {
        await transporter.sendMail({
            from: EMAIL_CONFIG.auth.user,
            to: EMAIL_CONFIG.recipient_emails.join(', '),
            subject: subject,
            text: body
        });
        console.log(`Email notification sent: ${subject}`);
    } catch (error) {
        console.error(`Failed to send email notification: ${error.message}`);
    }
}

// Create directories
function createDirs() {
    ['videos', 'videos/ipcam'].forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
            console.log(`Created directory: ${dir}`);
        }
    });
}

// Start FFmpeg
function startStream() {
    if (ffmpegProcess) {
        console.log('Killing existing FFmpeg process');
        ffmpegProcess.kill('SIGTERM');
        ffmpegProcess = null;
    }

    const ffmpeg = require('ffmpeg-static');
    console.log(`Starting FFmpeg for RTSP: ${RTSP_URL}`);
    ffmpegProcess = spawn(ffmpeg, [
        '-rtsp_transport', 'tcp',
        '-i', RTSP_URL,
        '-fflags', 'flush_packets',
        '-hls_time', '4',
        '-hls_list_size', '3',
        '-vcodec', 'copy',
        '-acodec', 'aac',
        '-hls_segment_filename', path.join(HLS_OUTPUT_DIR, 'segment%d.ts'),
        '-hls_flags', 'delete_segments+append_list',
        '-y', HLS_PLAYLIST
    ]);

    ffmpegProcess.stdout.on('data', (data) => {
        console.log(`FFmpeg stdout: ${data.toString().trim()}`);
    });

    ffmpegProcess.stderr.on('data', (data) => {
        console.error(`FFmpeg stderr: ${data.toString().trim()}`);
    });

    ffmpegProcess.on('exit', (code, signal) => {
        console.log(`FFmpeg exited with code ${code}, signal ${signal}`);
        ffmpegProcess = null;
        if (code !== 0 && code !== 255) {
            console.log('Restarting FFmpeg in 3 seconds...');
            setTimeout(startStream, 3000);
        }
    });

    setTimeout(checkStreamHealth, 10000);
}

// Check stream health
function checkStreamHealth() {
    if (!fs.existsSync(HLS_PLAYLIST) || !ffmpegProcess) {
        console.log('HLS playlist missing or FFmpeg not running. Restarting stream...');
        startStream();
    } else {
        setTimeout(checkStreamHealth, 10000);
    }
}

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('Shutting down server...');
    if (ffmpegProcess) {
        ffmpegProcess.kill('SIGTERM');
    }
    process.exit(0);
});

// Start server
createDirs();
startStream();

app.listen(port, '0.0.0.0', () => {
    console.log(`🔬 Lab Monitor running at http://192.168.1.35:${port}`);
    console.log(`📱 Compact widget: http://192.168.1.35:${port}`);
    console.log(`📺 Basic stream: http://192.168.1.35:${port}/stream`);
    console.log('📱 Compact widget ready for dashboard integration');
});