#!/bin/bash
# FILAMENT Consolidated Entrypoint
# Orchestrates Ollama and Filament App

set -e

# Start Ollama in the background
echo "[INFO] Starting Ollama service..."
ollama serve &

# Wait for Ollama to be ready
echo "[INFO] Waiting for Ollama to initialize..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 2
done

# Pull default models if needed
echo "[INFO] Ensuring llama3.2 is available..."
ollama pull llama3.2

echo "[INFO] Starting Filament Core..."
# Run the application as the filament user
exec su filament -c "python -m core"
