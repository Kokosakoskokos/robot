#!/usr/bin/env python3
import sys
import os
import subprocess
import importlib.util

def check_pkg(name):
    spec = importlib.util.find_spec(name)
    return "✅ OK" if spec is not None else "❌ CHYBÍ"

print("="*50)
print("CLANKER - DIAGNOSTIKA RASPBERRY PI")
print("="*50)

# 1. Kontrola Pythonu
print(f"Python verze: {sys.version.split()[0]}")

# 2. Kontrola knihoven
print("\n--- Knihovny ---")
libs = ["speech_recognition", "pyaudio", "cv2", "PIL", "numpy", "yaml"]
for lib in libs:
    print(f"{lib:20}: {check_pkg(lib)}")

# 3. Kontrola kamery
print("\n--- Kamera ---")
if os.path.exists("/dev/video0"):
    print("Video zařízení: /dev/video0 nalezeno ✅")
else:
    print("Video zařízení: NENALEZENO ❌")

# 4. Kontrola I2C (Serva)
print("\n--- I2C Sběrnice (Serva) ---")
try:
    i2c = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
    print(i2c.stdout)
except:
    print("i2cdetect: Příkaz selhal nebo I2C není povoleno ❌")

# 5. Kontrola zvuku
print("\n--- Zvuk (Audio) ---")
try:
    audio = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
    if "card" in audio.stdout:
        print("Výstupní zařízení: NALEZENO ✅")
    else:
        print("Výstupní zařízení: NENALEZENO ❌")
except:
    print("aplay: Kontrola zvuku selhala ❌")

print("\n" + "="*50)
print("Konec diagnostiky. Zkopíruj tento výstup a pošli mi ho.")
print("="*50)
