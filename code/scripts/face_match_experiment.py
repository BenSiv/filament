import face_recognition
import cv2
import json
import requests
import numpy as np
import os
from datetime import datetime

SKETCH_PATH = 'data/raw/sketch_1992.jpg'
CHARLEY_FILE = 'data/raw/charley_washington.json'
OUTPUT_FILE = 'data/processed/face_matches_1992.json'

def load_image_from_url(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            # Convert to numpy array
            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            # Decode
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if img is None: return None
            # Convert BGR to RGB (face_recognition uses RGB)
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except Exception as e:
        pass
    return None

def main():
    print(f"Loading sketch from {SKETCH_PATH}...")
    try:
        sketch_image = face_recognition.load_image_file(SKETCH_PATH)
        # Upsample 2x to help with sketch/small resolution
        sketch_encodings = face_recognition.face_encodings(sketch_image, num_jitters=5, model='large')
        
        if not sketch_encodings:
             print("CRITICAL: No face detected in the sketch. Attempting with lower threshold/upsampling...")
             # Try detecting locations first with CNN if available or HOG
             # Just fail gracefully for now if basic encoding fails.
             print("Experiment Aborted: Could not find face in sketch.")
             return
             
        sketch_encoding = sketch_encodings[0]
        print("Sketch encoded successfully.")
        
    except Exception as e:
        print(f"Error loading sketch: {e}")
        return

    # Load candidates
    with open(CHARLEY_FILE, 'r') as f:
        candidates = json.load(f)
        
    print(f"Scanning {len(candidates)} candidates for facial similarity...")
    
    matches = []
    
    for i, person in enumerate(candidates):
        images = person.get('images', [])
        name = person.get('name', 'Unknown')
        
        if not images:
            continue
            
        print(f"[{i+1}/{len(candidates)}] Checking {name}...")
        
        best_distance = 1.0 # High value = no match
        
        # Check first 2 images to save time
        for img_url in images[:2]:
            candidate_img = load_image_from_url(img_url)
            if candidate_img is not None:
                try:
                    c_encodings = face_recognition.face_encodings(candidate_img)
                    if c_encodings:
                        # Compare
                        distance = face_recognition.face_distance([sketch_encoding], c_encodings[0])[0]
                        if distance < best_distance:
                            best_distance = distance
                except:
                    pass
        
        # Store result if it's somewhat interesting (standard threshold is 0.6)
        # But we want "relatives" or vague matches, so maybe keep top results < 0.8
        if best_distance < 0.8:
            matches.append({
                'name': name,
                'url': person.get('url'),
                'score': float(best_distance), # Lower is better
                'similarity': (1 - float(best_distance)) * 100
            })
            
    # Sort by score (ascending distance)
    matches.sort(key=lambda x: x['score'])
    
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(matches, f, indent=2)
        
    print("\n--- TOP MATCHES ---")
    for m in matches[:10]:
        print(f"{m['name']} - Score: {m['score']:.4f} ({m['similarity']:.1f}%)")

if __name__ == "__main__":
    main()
