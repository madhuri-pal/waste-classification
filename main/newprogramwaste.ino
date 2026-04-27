

/*
   This code is used to control the robotic arm based on the inputs from the
   Raspberry Pi. The Raspberry Pi will detect the recycle and will tell the Arduino
   to move the robotic arm in the location the object is detected at. Based on
   the material, the robotic arm will place the object in the correct location.

   PROTOCOL: Python sends a single integer (1-5) representing the material:
     1 = cardboard, 2 = glass, 3 = metal, 4 = paper, 5 = plastic
   Arduino uses a fixed pickup position (distance preset 1) and rotates base
   to the correct drop-off bin based on material.
*/

// add Servo library
#include <Servo.h>

// ====== Configuration Constants ======
// Servo angle limits (clamp to safe range)
const int SERVO_MIN = 0;
const int SERVO_MAX = 180;

// Drop-off base angles for each material bin
const int BIN_CARDBOARD = 0;
const int BIN_GLASS = 45;
const int BIN_METAL = 90;
const int BIN_PAPER = 135;
const int BIN_PLASTIC = 180;

// create variables to store data from RPI
int material = 0;

// create variables to store servo positions
int shoulderPos = 90;
int elbowPos = 90;
int wrist1Pos = 90;
int wrist2Pos = 90;
int handPos = 90;
int basePos = 90;

// create Servo objects to control servos
Servo shoulder;
Servo elbow;
Servo wrist1;
Servo wrist2;
Servo hand;
Servo base;

// ====== Helper: Clamp angle to safe range ======
int clampAngle(int angle) {
  if (angle < SERVO_MIN) return SERVO_MIN;
  if (angle > SERVO_MAX) return SERVO_MAX;
  return angle;
}

// create flash function (will flash Arduino LED by the number you input)
void flash(int n) {
  for (int i = 0; i < n; i++) {
    digitalWrite(13, HIGH);
    delay(500);
    digitalWrite(13, LOW);
    delay(500);
  }
}

void setup() {
  // begin serial communication with RPI and send default string to RPI to confirm connection
  Serial.begin(9600);
  Serial.println("Connected to Arduino");

  // assign Arduino LED to pin 13
  pinMode(13, OUTPUT);

  // attach servo objects to correct pin number
  shoulder.attach(11);
  elbow.attach(10);
  wrist1.attach(9);
  wrist2.attach(6);
  hand.attach(5);
  base.attach(3);

  // move arm to home position to face camera down
  homeState();
}

void loop() {
  // send default string to RPI to confirm connection
  Serial.println("Connected to Arduino");

  // if the RPI sends a signal to Arduino
  if (Serial.available()) {
    // Read the material code (single integer 1-5)
    material = Serial.parseInt();

    // Validate material code
    if (material >= 1 && material <= 5) {
      Serial.print("[DEBUG] Received material code: ");
      Serial.println(material);

      // flash LED to indicate material received
      flash(material);

      // pick up the object and drop it off based on material
      pickUp();
      dropOff();

      // go back to home state
      homeState();

      // send string to let RPI know that the arm is done moving
      Serial.println("Done Moving");
      Serial.flush();
    } else {
      Serial.print("[DEBUG] Invalid material code received: ");
      Serial.println(material);
    }
  }
  delay(1000);
}

/*
   sweep function to make servos move slowly!

   input the servo object, the current servo angle, the angle you
   want the servo to move to, and the speed at which you want to turn
   the servo. Bigger number ==> slower speed. Smaller number ==> faster speed.
*/
void sweep(Servo servo, int oldPos, int newPos, int servoSpeed) {
  // Clamp target angle to safe range
  newPos = clampAngle(newPos);

  // Debug: log the servo movement
  Serial.print("[SERVO] Moving from ");
  Serial.print(oldPos);
  Serial.print(" to ");
  Serial.println(newPos);

  if (oldPos <= newPos) {
    for (int pos = oldPos; pos <= newPos; pos += 1) {
      servo.write(pos);
      delay(servoSpeed);
    }
  }
  else {
    for (int pos = oldPos; pos >= newPos; pos -= 1) {
      servo.write(pos);
      delay(servoSpeed);
    }
  }
}

// pickUp function — uses a fixed pickup position (closest distance preset)
void pickUp() {
  Serial.println("[ACTION] Picking up object...");

  // Rotate base to face forward (90 degrees = center/camera direction)
  sweep(base, basePos, 90, 30);
  basePos = 90;

  // Open hand
  sweep(hand, handPos, 160, 30);
  handPos = 160;

  // Position wrist
  sweep(wrist2, wrist2Pos, 35, 30);
  wrist2Pos = 35;

  // Extend elbow
  sweep(elbow, elbowPos, 180, 30);
  elbowPos = 180;

  // Lower shoulder
  sweep(shoulder, shoulderPos, 65, 30);
  shoulderPos = 65;

  // Close hand (grip the object)
  sweep(hand, handPos, 45, 30);
  handPos = 45;  // FIX: was incorrectly set to 180

  Serial.println("[ACTION] Object gripped.");
}

// dropOff function that will drop off the object to a location based off its material
void dropOff() {
  Serial.print("[ACTION] Dropping off material code: ");
  Serial.println(material);

  // First, lift the arm up to a safe carrying position
  sweep(shoulder, shoulderPos, 90, 15);
  shoulderPos = 90;
  sweep(elbow, elbowPos, 90, 30);   // FIX: was 0 which folds arm completely backward
  elbowPos = 90;
  sweep(wrist2, wrist2Pos, 90, 30);
  wrist2Pos = 90;

  // Rotate base to the correct bin based on material
  // FIX: was if(1) — constant true. Now properly checks material variable.
  if (material == 1) {
    // cardboard bin
    Serial.println("[BIN] Cardboard -> base angle 0");
    sweep(base, basePos, BIN_CARDBOARD, 30);
    basePos = BIN_CARDBOARD;
  }
  else if (material == 2) {
    // glass bin
    Serial.println("[BIN] Glass -> base angle 45");
    sweep(base, basePos, BIN_GLASS, 30);
    basePos = BIN_GLASS;
  }
  else if (material == 3) {
    // metal bin
    Serial.println("[BIN] Metal -> base angle 90");
    sweep(base, basePos, BIN_METAL, 30);
    basePos = BIN_METAL;
  }
  else if (material == 4) {
    // paper bin
    Serial.println("[BIN] Paper -> base angle 135");
    sweep(base, basePos, BIN_PAPER, 30);
    basePos = BIN_PAPER;
  }
  else if (material == 5) {
    // plastic bin
    Serial.println("[BIN] Plastic -> base angle 180");
    sweep(base, basePos, BIN_PLASTIC, 30);
    basePos = BIN_PLASTIC;
  }

  // Release the object
  sweep(hand, handPos, 160, 30);
  handPos = 160;  // FIX: was incorrectly set to 180

  Serial.println("[ACTION] Object released.");
}

// homeState function that will hold the camera facing down to perform object detection
void homeState() {
  Serial.println("[ACTION] Moving to home state...");

  sweep(base, basePos, 90, 30);
  basePos = 90;
  sweep(wrist2, wrist2Pos, 60, 30);
  wrist2Pos = 60;
  sweep(elbow, elbowPos, 110, 30);
  elbowPos = 110;
  sweep(shoulder, shoulderPos, 65, 30);
  shoulderPos = 65;
  sweep(hand, handPos, 90, 30);
  handPos = 90;  // FIX: was incorrectly set to 0

  Serial.println("[ACTION] Home state reached.");
}