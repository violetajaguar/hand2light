import cv2
import mediapipe as mp
import requests
from datetime import datetime, timedelta
import threading

# Twinkly Configuration - TWO SETS OF LIGHTS!
LIGHTS = [
    {"name": "Lights 1", "ip": "192.168.1.13"},
    {"name": "Lights 2", "ip": "192.168.1.14"}
]

# Token management for each light set
light_tokens = {}

def get_fresh_token(light_ip):
    """Get a new authentication token and verify it for a specific light"""
    try:
        base_url = f"http://{light_ip}/xled/v1"
        
        # Step 1: Login
        challenge = "1234"
        response = requests.post(
            f"{base_url}/login",
            headers={"Content-Type": "application/json"},
            json={"challenge": challenge},
            timeout=3
        )
        
        if response.status_code != 200:
            print(f"❌ {light_ip} login failed: {response.status_code}")
            return None
        
        data = response.json()
        auth_token = data.get("authentication_token")
        challenge_response = data.get("challenge-response")
        expires_in = data.get("authentication_token_expires_in", 14400)
        
        # Step 2: Verify token
        verify_response = requests.post(
            f"{base_url}/verify",
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": auth_token
            },
            json={"challenge-response": challenge_response},
            timeout=3
        )
        
        if verify_response.status_code != 200:
            print(f"❌ {light_ip} verify failed: {verify_response.status_code}")
            return None
        
        token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
        
        print(f"✅ {light_ip} token verified (expires in {expires_in}s)")
        
        return {
            "token": auth_token,
            "expires_at": token_expires_at,
            "ip": light_ip
        }
        
    except Exception as e:
        print(f"❌ {light_ip} token error: {e}")
        return None

def ensure_valid_token(light_ip):
    """Make sure we have a valid token for a specific light"""
    if light_ip not in light_tokens or light_tokens[light_ip] is None:
        light_tokens[light_ip] = get_fresh_token(light_ip)
        return light_tokens[light_ip] is not None
    
    token_info = light_tokens[light_ip]
    if datetime.now() >= token_info["expires_at"]:
        light_tokens[light_ip] = get_fresh_token(light_ip)
        return light_tokens[light_ip] is not None
    
    return True

def play_effect_on_light(light_ip, effect_id):
    """Send command to play a movie effect on a specific light"""
    if not ensure_valid_token(light_ip):
        return False
    
    try:
        token = light_tokens[light_ip]["token"]
        base_url = f"http://{light_ip}/xled/v1"
        
        r = requests.post(
            f"{base_url}/movies/current",
            headers={
                "X-Auth-Token": token,
                "Content-Type": "application/json"
            },
            json={"id": effect_id},
            timeout=2
        )
        
        if r.status_code == 200:
            return True
        else:
            if r.status_code == 401:
                # Token invalid, force refresh
                light_tokens[light_ip] = None
            return False
            
    except Exception as e:
        return False

def play_effect(effect_id):
    """Play the same effect on ALL light sets simultaneously"""
    threads = []
    results = {}
    
    def play_on_light(light_info):
        ip = light_info["ip"]
        success = play_effect_on_light(ip, effect_id)
        results[ip] = success
    
    # Start all requests in parallel
    for light in LIGHTS:
        thread = threading.Thread(target=play_on_light, args=(light,))
        thread.start()
        threads.append(thread)
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    # Report results
    success_count = sum(1 for s in results.values() if s)
    status = "✅" if success_count == len(LIGHTS) else "⚠️"
    print(f"🔥 LIGHTS → Effect #{effect_id} {status} ({success_count}/{len(LIGHTS)} sets)")

# Initialize connection to ALL lights
print("🎯 INITIALIZING DUAL LIGHT CONTROL...")
print(f"📡 Connecting to {len(LIGHTS)} light sets...")

failed_lights = []
for light in LIGHTS:
    token_info = get_fresh_token(light["ip"])
    if token_info:
        light_tokens[light["ip"]] = token_info
    else:
        failed_lights.append(light["name"])

if len(failed_lights) == len(LIGHTS):
    print("❌ Failed to connect to any lights!")
    print("💡 Check: 1) IP addresses are correct, 2) Lights are on same network")
    exit(1)
elif failed_lights:
    print(f"⚠️  Connected to some lights, but {', '.join(failed_lights)} failed")
else:
    print(f"🎉 All {len(LIGHTS)} light sets connected!")

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

print("🎉 DUAL HAND CONTROL ACTIVE!")
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
    
    # Show connected lights status
    connected = len([ip for ip in light_tokens if light_tokens[ip] is not None])
    cv2.putText(frame, f"LIGHTS: {connected}/{len(LIGHTS)}", (50, 220), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 3)
    
    cv2.imshow('🎯 DUAL LIGHT CONTROL!', frame)
    
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("🎉 You are now a DUAL Twinkly wizard!")

