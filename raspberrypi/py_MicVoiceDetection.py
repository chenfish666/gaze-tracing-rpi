import pyaudio
import wave
import numpy as np
import time

# Audio Config
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2    # Keep stereo
RATE = 16000

def get_input_device_index(p):
    """
    Automatically find the index ID for 'seeed-2mic-voicecard'
    Avoids PyAudio picking default HDMI or other devices.
    """
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info.get('name')
        # Look for keyword 'seeed'
        if 'seeed' in name.lower():
            print(f"[Audio] Found ReSpeaker at index {i}: {name}")
            return i
    
    print("[Audio] Warning: ReSpeaker not found, using default device.")
    return None

def record(filename="wake.wav", threshold=0.08, max_duration=10):
    p = pyaudio.PyAudio()
    
    # 1. Automatically get correct device ID
    dev_index = get_input_device_index(p)

    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=dev_index, # Explicitly set device
                        frames_per_buffer=CHUNK)
        
        print(f"[VAD] Listening... (Threshold: {threshold})")
        frames = []
        is_recording = False
        silence_start = None
        start_time = None
        
        # Dynamic threshold (Map 0.0-1.0 to int16 range)
        THRESH_INT = int(threshold * 32768)
        SILENCE_LIMIT = 1.0 

        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            
            # --- CRITICAL FIX START ---
            # 1. Convert to int16 array
            audio_data_int16 = np.frombuffer(data, dtype=np.int16)
            
            # 2. Convert to float32 to prevent overflow
            # int16 squaring often overflows to negative, causing sqrt errors
            audio_data_float = audio_data_int16.astype(np.float32)
            
            # 3. Calculate volume (RMS)
            volume = np.sqrt(np.mean(audio_data_float**2))
            # --- CRITICAL FIX END ---

            # Debug: If no response, uncomment below to check current volume
            # print(f"Current Volume: {int(volume)} | Threshold: {THRESH_INT}")

            if not is_recording:
                # Trigger recording
                if volume > THRESH_INT:
                    print(f"\n[VAD] Sound detected! (Vol: {int(volume)}) Recording...")
                    is_recording = True
                    start_time = time.time()
                    frames.append(data)
            else:
                # Continue recording
                frames.append(data)
                
                # Check silence
                if volume < THRESH_INT:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_LIMIT:
                        print("[VAD] Silence detected. Done.")
                        break
                else:
                    silence_start = None 

                # Check timeout
                if time.time() - start_time > max_duration:
                    print("[VAD] Max duration reached.")
                    break
        
        # Save file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return filename

    except Exception as e:
        print(f"[VAD] Error: {e}")
        return None
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except: pass
        p.terminate()

# Simple test block if run directly
if __name__ == "__main__":
    record("test_output.wav")