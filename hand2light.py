import cv2
import mediapipe as mp
import requests
from datetime import datetime, timedelta
import hashlib

# Twinkly Configuration
LIGHTS_IP = "192.168.1.13"  # Your actual lights IP
BASE_URL = f"http://{LIGHTS_IP}/xled/v1"

# Token management
auth_token = None
token_expires_at = None
session = requests.Session()

def get_fresh_token():
    """Get a new authentication token and verify it"""
    global auth_token, token_expires_at, session
    
    try:
        # Step 1: Login
        challenge = "1234"
        response = requests.post(
            f"{BASE_URL}/login",
            headers={"Content-Type": "application/json"},
            json={"challenge": challenge},
            timeout=3
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        data = response.json()
        auth_token = data.get("authentication_token")
        challenge_response = data.get("challenge-response")
        expires_in = data.get("authentication_token_expires_in", 14400)
        
        # Step 2: Verify token (THIS WAS MISSING!)
        verify_response = requests.post(
            f"{BASE_URL}/verify",
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": auth_token
            },
            json={"challenge-response": challenge_response},
            timeout=3
        )
        
        if verify_response.status_code != 200:
            print(f"❌ Verify failed: {verify_response.status_code}")
            return False
        
        token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        
        # Update session headers
        session.headers.update({
            "X-Auth-Token": auth_token,
            "Content-Type": "application/json"
        })
        
        print(f"✅ Token verified and ready (expires in {expires_in}s)")
        return True
        
    except Exception as e:
        print(f"❌ Token error: {e}")
        return False

def ensure_valid_token():
    """Make sure we have a valid token"""
    if auth_token is None or token_expires_at is None or datetime.now() >= token_expires_at:
        return get_fresh_token()
    return True

def play_effect(effect_id):
    """Send command to play a movie effect"""
    if not ensure_valid_token():
        print("⚠️ Cannot play effect - no valid token")
        return
    
    try:
        r = session.post(f"{BASE_URL}/movies/current", json={"id": effect_id}, timeout=2)
        
        if r.status_code == 200:
            print(f"🔥 LIGHTS → Effect #{effect_id} ✅")
        else:
            print(f"🔥 LIGHTS → Effect #{effect_id} ⚠️ ({r.status_code})")
            # If token invalid, force refresh
            if r.status_code == 401:
                global auth_token
                auth_token = None
    except Exception as e:
        print(f"⚠️ Failed to send effect #{effect_id}: {e}")

# Initialize connection
print("🎯 INITIALIZING HAND CONTROL...")
if not get_fresh_token():
    print("❌ Failed to connect to lights at", LIGHTS_IP)
    print("💡 Check: 1) IP address is correct, 2) Lights are on same network")
    exit(1)

# MediaPipe setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

EFFECTS = {
    0: 9,   # Sun
    1: 1,   # Starry
    2: 6,   # Rainbow Rain
    3: 11,  # Warm Swirl
    4: 12,  # Pale Rainbow
    5: 8,   # Geomatrix
    6: 4,   # Selfie
    7: 7,   # Frida
    8: 2,   # Christmas
    9: 3,   # Blueberries
    10: 5   # Mondri Anne
}

print("🎉 FINAL HAND CONTROL - VERIFIED TOKEN!")
print("✌️+✌️ = 6 = SELFIE | 🖐️+🖐️ = 8 = CHRISTMAS | 🙌+🙌 = 10 = MONDRI")

current = None

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    
    fingers = 0
    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS,
                                 mp_draw.DrawingSpec(color=(0,255,0), thickness=3),
                                 mp_draw.DrawingSpec(color=(255,0,0), thickness=3))
            for tip, pip in zip([4,8,12,16,20], [2,5,9,13,17]):
                if hand.landmark[tip].y < hand.landmark[pip].y:
                    fingers += 1
    
    if fingers in EFFECTS and fingers != current:
        play_effect(EFFECTS[fingers])
        current = fingers
    
    cv2.putText(frame, f"TOTAL FINGERS: {fingers}", (50, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,0), 5)
    
    name = {4:"SELFIE", 7:"FRIDA", 2:"CHRISTMAS", 5:"MONDRI", 9:"SUN"}.get(
        EFFECTS.get(fingers, 0), ""
    )
    if name:
        cv2.putText(frame, name, (50, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,255), 5)
    
    cv2.imshow('🎯 FINAL HAND CONTROL - WORKING!', frame)
    
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("🎉 You are now a Twinkly wizard!")
