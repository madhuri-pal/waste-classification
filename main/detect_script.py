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

# ====== Material Code Mapping ======
# Maps label string -> integer code that Arduino expects
MATERIAL_CODES = {
    "cardboard": 1,
    "glass": 2,
    "metal": 3,
    "paper": 4,
    "plastic": 5
}

# ====== Load Labels ======
labels = {}
with open(LABELS_PATH, "r") as f:
    for i, line in enumerate(f.readlines()):
        labels[i] = line.strip()

print(f"[INFO] Loaded labels: {labels}")

# ====== Load TFLite Model ======
print("[INFO] Loading model...")
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
_, height, width, _ = input_details[0]['shape']
print(f"[INFO] Model loaded. Input size: {width}x{height}")

# ====== Setup Serial Connection ======
try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # wait for Arduino to be ready
    print(f"[INFO] Serial connected to {SERIAL_PORT}")
except Exception as e:
    arduino = None
    print(f"[WARNING] Serial not connected: {e}")

# ====== Function to Send Command ======
def send_command_to_arduino(material_code):
    """
    Send a single integer material code to Arduino.
    Protocol: Arduino expects a single integer (1-5) via Serial.parseInt().
    """
    if arduino:
        command = f"{material_code}\n"
        print(f"[SEND] Material code {material_code} → Arduino")
        arduino.write(command.encode())
        time.sleep(0.1)

        # Wait for Arduino to finish moving (read "Done Moving" response)
        print("[WAIT] Waiting for Arduino to finish...")
        start_time = time.time()
        timeout = 30  # 30 second timeout for arm movement
        while time.time() - start_time < timeout:
            if arduino.in_waiting > 0:
                response = arduino.readline().decode().strip()
                print(f"[ARDUINO] {response}")
                if response == "Done Moving":
                    print("[OK] Arduino finished moving.")
                    return True
            time.sleep(0.1)
        print("[TIMEOUT] Arduino did not respond in time.")
        return False
    else:
        print(f"[MOCK SEND] Would send material code → {material_code}")
        return True

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
                    # Get the material code for this label
                    material_code = MATERIAL_CODES.get(label)
                    if material_code is not None:
                        print(f"[TRIGGER] {label} detected {DETECTION_THRESHOLD} times → sending code {material_code}")
                        send_command_to_arduino(material_code)
                    else:
                        print(f"[ERROR] No material code mapping for label: {label}")

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
