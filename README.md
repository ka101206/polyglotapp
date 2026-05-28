# Polyglot TTS Desktop Application

A fully containerized, multi-lingual AI Text-To-Speech (TTS) application running inside a virtual Linux desktop. It uses the highly optimized Kokoro-ONNX and Piper-TTS engines to provide ultra-realistic speech synthesis in English, Japanese, Chinese, Korean, Spanish, French, and Italian.

## 🚀 Getting Started

Because the AI language models are massive (300MB+), they are not included in this Git repository. You must download them before running the application.

### 1. Download the AI Models

You can download all required models automatically using the provided script:

```bash
chmod +x download_models.sh
./download_models.sh
```

Alternatively, you can manually download the following files and place them in the project root:
- `kokoro-v1.0.onnx`
- `voices.bin`
- `models/es_ES-sharvard-medium.onnx`
- `models/fr_FR-tom-medium.onnx`
- `models/it_IT-riccardo-x_low.onnx`

### 2. Run the Application (Docker)

This application is fully containerized. To launch it, simply run:

```bash
docker compose up -d
```

### 3. Connect to the GUI

Once the container is running, open your web browser and navigate to:
**http://localhost:8080/vnc.html**

Click **Connect** to access the virtual desktop and interact with the TTS interface!

### 🛑 Stopping the Application

To shut down the web server and the virtual desktop, run:
```bash
docker compose down
```
