#!/bin/bash
set -e

echo "========================================="
echo "Downloading Polyglot TTS Models"
echo "========================================="

# Create models directory if it doesn't exist
mkdir -p models

# Download Kokoro ONNX model and Voices
echo "Downloading Kokoro ONNX (300MB)..."
curl -L -o kokoro-v1.0.onnx "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v1.0.onnx"

echo "Downloading Kokoro Voices (30MB)..."
curl -L -o voices.bin "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"

# Download European Piper Models
echo "Downloading Spanish Model..."
curl -L -o models/es_ES-sharvard-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx"

echo "Downloading French Model..."
curl -L -o models/fr_FR-tom-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx"

echo "Downloading Italian Model..."
curl -L -o models/it_IT-riccardo-x_low.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx"

echo "========================================="
echo "✅ All models downloaded successfully!"
echo "You can now run: docker compose up -d"
echo "========================================="
