#!/bin/bash

# Instalacja zależności systemowych
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev portaudio19-dev libasound2-dev ffmpeg

# Tworzenie i aktywacja środowiska wirtualnego
python3 -m venv venv
source venv/bin/activate

# Instalacja zależności Pythona
pip install --upgrade pip
pip install -r requirements.txt

# Uruchomienie skryptu pobierania modelu
./setup_model.sh
