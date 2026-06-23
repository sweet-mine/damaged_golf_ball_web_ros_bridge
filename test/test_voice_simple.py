import os
import wave
import struct
import requests
import json

# 1. Generate 1 second of silent WAV
wav_path = "test_silent.wav"
with wave.open(wav_path, "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    for i in range(16000):
        data = struct.pack('<h', 0)
        f.writeframesraw(data)

print(f"Generated test file: {wav_path}")

# 2. Upload to the voice endpoint
url = "http://localhost:8000/api/agent/voice"
files = {
    "file": (wav_path, open(wav_path, "rb"), "audio/wav")
}
data = {
    "history": json.dumps([])
}

print(f"Sending POST request to {url}...")
try:
    response = requests.post(url, files=files, data=data)
    print("Response Status:", response.status_code)
    print("Response Body:", response.json())
except Exception as e:
    print("Request failed:", e)

# 3. Clean up
if os.path.exists(wav_path):
    os.remove(wav_path)
