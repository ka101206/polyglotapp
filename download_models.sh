#!/bin/bash
set -e

echo "========================================="
echo "Downloading Polyglot TTS Models"
echo "========================================="

# Create models directory if it doesn't exist
mkdir -p models

# Download Kokoro ONNX model and Voices
echo "Downloading Kokoro ONNX (300MB)..."
curl -fL -o kokoro-v1.0.onnx "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"

echo "Downloading Kokoro Voices (30MB)..."
curl -fL -o voices.bin "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

# Download European Piper Models
echo "Downloading Spanish Model..."
curl -fL -o models/es_ES-sharvard-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"

echo "Downloading French Model..."
curl -fL -o models/fr_FR-tom-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx"

echo "Downloading Italian Model..."
curl -fL -o models/it_IT-riccardo-x_low.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx"

echo "========================================="
echo "✅ All models downloaded successfully!"
echo "You can now run: docker compose up -d"
echo "========================================="
