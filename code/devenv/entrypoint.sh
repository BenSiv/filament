#!/bin/bash
# FILAMENT Consolidated Entrypoint
# Orchestrates Ollama and Filament App

set -e

# Start Ollama in the background
echo "[INFO] Starting Ollama service"
ollama serve &

# Wait for Ollama to be ready
echo "[INFO] Waiting for Ollama to initialize"
ollama --version
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 2
done

echo "[INFO] Current models before pull:"
curl -s http://localhost:11434/api/tags

# Pull default models if needed
echo "[INFO] Ensuring deepseek-r1:1.5b is available"
ollama pull deepseek-r1:1.5b

echo "[INFO] Models after pull:"
curl -s http://localhost:11434/api/tags

echo "[INFO] Starting Filament Core"
# Run the application as the filament user
exec su filament -c "python -m core"
