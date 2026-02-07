import face_recognition
import cv2
import sys

def test_detection(image_path):
    print(f"Testing detection on {image_path}")
    try:
        # Load
        image = face_recognition.load_image_file(image_path)
        
        # Detect
        # upsell=2 to help with small images
        face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=2, model="hog")
        
        print(f"Found {len(face_locations)} faces.")
        
        if len(face_locations) > 0:
             # Try encoding
             encodings = face_recognition.face_encodings(image, face_locations)
             print(f"Successfully generated {len(encodings)} encodings.")
             return True
        else:
             print("No faces detected.")
             return False
             
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_detection('data/raw/sketch_1992.jpg')
