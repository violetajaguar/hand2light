# hand2light 🖐️💡

**hand2light** is an embodied light system where gestures become commands and light responds.

Using real-time hand tracking, human movement controls Twinkly LED effects locally, turning the body into an interface.  
Built for live performance, installations, and playful human–machine interaction.

The project includes both a **single-light version** and a **multi-light version** for installation-scale setups.

---

## What it does

- Tracks hands in real time via webcam  
- Counts fingers across one or two hands  
- Maps gestures to Twinkly LED movie effects  
- Communicates with lights over the local network (no cloud)  
- Designed for low-latency, live situations  

---

## Tech stack

- Python 3.11  
- OpenCV  
- MediaPipe Hands  
- Twinkly Local API  
- Requests / NumPy  

---

## How it works (high level)

1. Webcam captures live video  
2. MediaPipe detects hand landmarks  
3. Finger count is calculated  
4. Each gesture triggers a predefined light effect  
5. Commands are sent directly to Twinkly lights over LAN  

The system auto-handles Twinkly authentication and token verification.

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

