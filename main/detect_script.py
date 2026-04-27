import cv2
import numpy as np
import time


import serial
from tensorflow.lite.python.interpreter import Interpreter

# ====== Configurations ======
MODEL_PATH = r"C:\Users\GHRCE\Downloads\Waste Sorting Arm (1)\newprogramwaste\detect.tflite"
LABELS_PATH = r"C:\Users\GHRCE\Downloads\Waste Sorting Arm (1)\newprogramwaste\labels.txt"
SERIAL_PORT = "COM7"         # Change this to your Arduino port
BAUD_RATE = 9600
CONFIDENCE_THRESHOLD = 0.5
DETECTION_THRESHOLD = 5       # Send to Arduino after consistent detections
INPUT_IMAGE_SIZE = (300, 300) # Match your model input size

# ====== Load Labels ======
labels = {}
with open(LABELS_PATH, "r") as f:
    for i, line in enumerate(f.readlines()):
        labels[i] = line.strip()

# ====== Load TFLite Model ======
print("[INFO] Loading model...")
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
_, height, width, _ = input_details[0]['shape']

# ====== Setup Serial Connection ======
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # wait for Arduino to be ready
    print(f"[INFO] Serial connected to {SERIAL_PORT}")
except:
    arduino = None
    print("[WARNING] Serial not connected. Check your port.")

# ====== Function to Send Command ======
def send_command_to_arduino(code):
    if arduino:
        print(f"[SEND COMMAND] → {code}")
        arduino.write(f"{code}\n".encode())
        time.sleep(0.1)
    else:
        print(f"[MOCK SEND] Would send → {code}")

# ====== Start Webcam ======
cap = cv2.VideoCapture(0)
print("[INFO] Starting webcam...")

# ====== Detection Counters ======
object_counts = {
    "cardboard": 0,
    "glass": 0,
    "metal": 0,
    "paper": 0,
    "plastic": 0
}

while True:
    ret, frame = cap.read()
    if not ret:
        break

    input_image = cv2.resize(frame, (width, height))
    input_data = np.expand_dims(input_image, axis=0).astype(np.uint8)

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    boxes = interpreter.get_tensor(output_details[0]['index'])[0]
    classes = interpreter.get_tensor(output_details[1]['index'])[0].astype(int)
    scores = interpreter.get_tensor(output_details[2]['index'])[0]

    for i in range(len(scores)):
        confidence = scores[i]
        if confidence > CONFIDENCE_THRESHOLD:
            class_id = classes[i]
            label = labels.get(class_id, "Unknown")

            # Draw bounding box
            ymin, xmin, ymax, xmax = boxes[i]
            (startX, startY, endX, endY) = (int(xmin * frame.shape[1]), int(ymin * frame.shape[0]),
                                            int(xmax * frame.shape[1]), int(ymax * frame.shape[0]))
            cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} ({confidence:.2f})", (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Log and count detection
            print(f"Detected: {label} with confidence {confidence:.2f}")
            if label in object_counts:
                object_counts[label] += 1

                if object_counts[label] >= DETECTION_THRESHOLD:
                    # Send code once detection threshold reached
                    if label == "cardboard":
                        send_command_to_arduino(1)
                    elif label == "glass":
                        send_command_to_arduino(2)
                    elif label == "metal":
                        send_command_to_arduino(3)
                    elif label == "paper":
                        send_command_to_arduino(4)
                    elif label == "plastic":
                        send_command_to_arduino(5)

                    object_counts = {k: 0 for k in object_counts}  # reset all counts
                    break

    cv2.imshow("Waste Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ====== Cleanup ======
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
    print("[INFO] Serial disconnected.")
