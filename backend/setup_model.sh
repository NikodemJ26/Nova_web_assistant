#!/bin/bash

# Utwórz katalog na modele
mkdir -p models/vosk

# Pobierz model Vosk dla języka polskiego
wget https://alphacephei.com/vosk/models/vosk-model-pl-spk-0.22.zip -O models/vosk/vosk-model-pl.zip

# Rozpakuj model
unzip models/vosk/vosk-model-pl.zip -d models/vosk/pl

# Usuń archiwum
rm models/vosk/vosk-model-pl.zip

echo "Model Vosk został pomyślnie pobrany i zainstalowany."
