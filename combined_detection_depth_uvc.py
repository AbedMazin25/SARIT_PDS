#!/usr/bin/env python3
"""
Integrated OAK-D Detection System with Simple Detection Alerts
Combines object detection and UVC output with simplified alarm system.
Plays chiller sound whenever objects are detected.
"""

import cv2
import depthai as dai
import numpy as np
import time
import argparse
import threading
import socket
import json
from queue import Queue, Empty

# Jetson Inference imports
from jetson_inference import detectNet
import jetson_utils

# Pygame for sound alerts
import pygame

# ────────────────────────────────────────────────────────────────────
# Configuration Settings
# ────────────────────────────────────────────────────────────────────
DISPLAY_OUTPUT = True               # Set to False for headless deployment
ENABLE_ALERTS = True                # Enable sound alerts
SEND_DATA_TO_EMULATOR = True        # Send detection status to emulator app
EMULATOR_IP = "127.0.0.1"          # IP address of emulator app
EMULATOR_PORT = 5555                # Port of emulator app

# Detection model settings
DETECTION_MODEL = "ssd-mobilenet-v2"
DETECTION_THRESHOLD = 0.5

# ────────────────────────────────────────────────────────────────────
# Parse Arguments
# ────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description='Integrated OAK-D Detection System')
parser.add_argument('-fb', '--flash-bootloader', default=False, action="store_true")
parser.add_argument('-f', '--flash-app', default=False, action="store_true")
parser.add_argument('-l', '--load-and-exit', default=False, action="store_true")
parser.add_argument('--uvc-only', default=False, action="store_true", 
                   help="Run UVC output only without detection display")
parser.add_argument('--no-sound', default=False, action="store_true",
                   help="Disable sound alerts")
parser.add_argument('--no-emulator', default=False, action="store_true",
                   help="Disable emulator communication")
parser.add_argument('--headless', default=False, action="store_true",
                   help="Run without visual display")
args = parser.parse_args()

# Override settings based on arguments
if args.no_sound:
    ENABLE_ALERTS = False
if args.no_emulator:
    SEND_DATA_TO_EMULATOR = False
if args.headless:
    DISPLAY_OUTPUT = False

if args.load_and_exit:
    import os
    os.environ["DEPTHAI_WATCHDOG"] = "0"

# ────────────────────────────────────────────────────────────────────
# Vehicle Classes and Label Mapping
# ────────────────────────────────────────────────────────────────────
VEHICLE_CLASSES = {
    'person': True,
    'bicycle': True,
    'car': True,
    'motorcycle': True,
    'bus': True,
    'truck': True
}

# ────────────────────────────────────────────────────────────────────
# Initialize Systems
# ────────────────────────────────────────────────────────────────────

# Initialize jetson-inference detection network
print(f"Loading detection model: {DETECTION_MODEL}")
net = detectNet(DETECTION_MODEL, threshold=DETECTION_THRESHOLD)

# Initialize sound system
sound_enabled = False
current_playing_sound = None
if ENABLE_ALERTS:
    try:
        pygame.mixer.init()
        pygame.init()
        # Load the chiller sound file
        CHILLER_SOUND = pygame.mixer.Sound("sounds/low warning user.mp3")
        CHILLER_SOUND.set_volume(0.5)
        sound_enabled = True
        print("Sound system initialized")
    except Exception as e:
        print(f"Warning: Could not initialize sound system: {e}")
        sound_enabled = False

# Initialize emulator communication
emulator_enabled = False
emulator_socket = None
if SEND_DATA_TO_EMULATOR:
    try:
        emulator_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        emulator_enabled = True
        print(f"Emulator communication enabled: {EMULATOR_IP}:{EMULATOR_PORT}")
    except Exception as e:
        print(f"Warning: Could not initialize emulator communication: {e}")
        emulator_enabled = False

# ────────────────────────────────────────────────────────────────────
# Core Functions
# ────────────────────────────────────────────────────────────────────

def getPipeline():
    """Create and configure the DepthAI pipeline"""
    pipeline = dai.Pipeline()

    # RGB camera for object detection and UVC output
    cam_rgb = pipeline.createColorCamera()
    cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    cam_rgb.setInterleaved(False)
    cam_rgb.setPreviewSize(640, 480)
    cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
    cam_rgb.setFps(30)
    cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)

    # UVC output
    uvc = pipeline.createUVC()
    cam_rgb.video.link(uvc.input)

    # Output streams
    rgb_out = pipeline.createXLinkOut()
    rgb_out.setStreamName("rgb")
    cam_rgb.preview.link(rgb_out.input)

    # Configure UVC
    config = dai.Device.Config()
    config.board.uvc = dai.BoardConfig.UVC(1920, 1080)
    config.board.uvc.frameType = dai.ImgFrame.Type.NV12
    pipeline.setBoardConfig(config.board)

    return pipeline

def flash(pipeline=None):
    """Flash bootloader or application pipeline"""
    from depthai import DeviceBootloader
    (f, bl) = DeviceBootloader.getFirstAvailableDevice()
    bootloader = DeviceBootloader(bl, True)
    
    progress = lambda p: print(f'Flashing progress: {p*100:.1f}%')
    
    startTime = time.monotonic()
    if pipeline is None:
        print("Flashing bootloader...")
        bootloader.flashBootloader(progress)
    else:
        print("Flashing application pipeline...")
        bootloader.flash(progress, pipeline)
    
    print(f"Done in {time.monotonic() - startTime:.2f} seconds")

def jetson_object_detection(frame):
    """Perform object detection using jetson-inference"""
    try:
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = frame
        
        height, width = rgb_frame.shape[:2]
        cuda_img = jetson_utils.cudaFromNumpy(rgb_frame)
        
        detections = net.Detect(cuda_img, width, height)
        
        detection_results = []
        for detection in detections:
            class_id = detection.ClassID
            class_name = net.GetClassDesc(class_id)
            confidence = detection.Confidence
            
            # Only include vehicle-related classes
            if class_name.lower() in VEHICLE_CLASSES:
                left = int(detection.Left)
                top = int(detection.Top)
                right = int(detection.Right)
                bottom = int(detection.Bottom)
                
                detection_results.append({
                    'bbox': [left, top, right, bottom],
                    'class': class_name,
                    'confidence': confidence
                })
        
        return detection_results
        
    except Exception as e:
        print(f"Detection error: {e}")
        return []

def play_alert_sound(has_detections):
    """Play chiller sound when objects are detected"""
    global current_playing_sound
    if not sound_enabled:
        return
    
    if has_detections:
        # Play chiller sound if not already playing
        if current_playing_sound != "chiller":
            pygame.mixer.stop()
            CHILLER_SOUND.play(loops=-1)
            current_playing_sound = "chiller"
    else:
        # Stop sound when no detections
        if current_playing_sound is not None:
            pygame.mixer.stop()
            current_playing_sound = None

def send_to_emulator(has_detections):
    """Send detection status to emulator"""
    if not emulator_enabled:
        return
    
    try:
        detection_level = 50 if has_detections else 0  # Simple binary state
        message = json.dumps({"danger_level": detection_level})
        emulator_socket.sendto(message.encode('utf-8'), (EMULATOR_IP, EMULATOR_PORT))
    except Exception as e:
        print(f"Error sending to emulator: {e}")

def draw_detections(frame, detections):
    """Draw bounding boxes for detected objects"""
    if not detections:
        return frame
    
    for detection in detections:
        x1, y1, x2, y2 = detection['bbox']
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Use green color for all detections
        color = (0, 255, 0)
        thickness = 2
        
        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        
        # Prepare label
        label = f"{detection['class']}: {detection['confidence']:.2f}"
        
        # Draw label background
        (label_width, label_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - label_height - 10), (x1 + label_width, y1), color, -1)
        
        # Draw label text
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Draw center point
        cv2.circle(frame, (center_x, center_y), 5, color, -1)
    
    return frame

class FrameProcessor:
    """Thread-safe frame processor for object detection"""
    
    def __init__(self):
        self.rgb_queue = Queue(maxsize=2)
        self.result_queue = Queue(maxsize=2)
        self.detection_thread = None
        self.running = False
        
    def start(self):
        self.running = True
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
    
    def stop(self):
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
    
    def _detection_worker(self):
        """Background thread for object detection"""
        while self.running:
            try:
                rgb_frame = self.rgb_queue.get(timeout=0.1)
                detections = jetson_object_detection(rgb_frame)
                
                if not self.result_queue.full():
                    self.result_queue.put(detections)
                    
            except Empty:
                continue
            except Exception as e:
                print(f"Detection thread error: {e}")
    
    def add_rgb_frame(self, frame):
        """Add RGB frame for processing"""
        try:
            self.rgb_queue.put_nowait(frame)
        except:
            pass  # Skip if queue is full
    
    def get_latest_detection(self):
        """Get latest detection results"""
        try:
            return self.result_queue.get_nowait()
        except Empty:
            return None

# ────────────────────────────────────────────────────────────────────
# Main Application
# ────────────────────────────────────────────────────────────────────

def main():
    # Handle flashing operations
    if args.flash_bootloader or args.flash_app:
        if args.flash_bootloader:
            flash()
        if args.flash_app:
            flash(getPipeline())
        print("Flashing successful. Please power-cycle the device")
        return

    # Create pipeline
    pipeline = getPipeline()

    # Handle load-and-exit mode for UVC
    if args.load_and_exit:
        device = dai.Device(pipeline)
        print("\nUVC device started. Check UVC viewer for camera stream.")
        print("To reconnect with depthai, a device power-cycle may be required")
        import signal
        import os
        os.kill(os.getpid(), signal.SIGTERM)

    # Standard operation
    try:
        with dai.Device(pipeline) as device:
            print("\n" + "="*60)
            print("INTEGRATED OAK-D DETECTION SYSTEM")
            print("="*60)
            print(f"• Object Detection: {DETECTION_MODEL}")
            print(f"• Sound Alerts: {'ENABLED' if sound_enabled else 'DISABLED'}")
            print(f"• Emulator Communication: {'ENABLED' if emulator_enabled else 'DISABLED'}")
            print(f"• Display Output: {'ENABLED' if DISPLAY_OUTPUT else 'DISABLED'}")
            print(f"• UVC Output: ENABLED")
            print("="*60)
            
            if args.uvc_only:
                print("UVC-only mode: Check UVC viewer for camera stream")
                print("Press Ctrl+C to exit")
                try:
                    while True:
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    pass
                return

            # Initialize queues
            rgb_queue = device.getOutputQueue(name="rgb", maxSize=2, blocking=False)

            # Initialize frame processor
            processor = FrameProcessor()
            processor.start()

            # Performance tracking
            fps_counter = 0
            fps_timer = time.time()
            current_detections = []

            print("System running... Press 'q' to quit")

            try:
                while True:
                    # Get latest frames
                    rgb_frame = None

                    # Process RGB frame
                    if rgb_queue.has():
                        rgb_in = rgb_queue.get()
                        rgb_frame = rgb_in.getCvFrame()
                        processor.add_rgb_frame(rgb_frame.copy())

                    # Get latest detections
                    latest_detections = processor.get_latest_detection()
                    if latest_detections is not None:
                        current_detections = latest_detections

                    # Handle alerts based on detection presence
                    has_detections = len(current_detections) > 0
                    
                    # Send to emulator
                    if emulator_enabled:
                        send_to_emulator(has_detections)
                    
                    # Play sound alerts
                    if sound_enabled:
                        play_alert_sound(has_detections)

                    # Display processing
                    if DISPLAY_OUTPUT and rgb_frame is not None:
                        # Draw detections
                        display_frame = draw_detections(rgb_frame, current_detections)
                        
                        # Add detection status indicator
                        if has_detections:
                            cv2.rectangle(display_frame, (20, 20), (200, 40), (0, 255, 0), -1)
                            cv2.putText(display_frame, "OBJECTS DETECTED", (25, 35),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                        else:
                            cv2.rectangle(display_frame, (20, 20), (200, 40), (128, 128, 128), -1)
                            cv2.putText(display_frame, "NO OBJECTS", (25, 35),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                        # Performance info
                        fps_counter += 1
                        if time.time() - fps_timer >= 1.0:
                            fps = fps_counter
                            
                            cv2.putText(display_frame, f"FPS: {fps}", (10, display_frame.shape[0] - 40),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            cv2.putText(display_frame, f"Objects: {len(current_detections)}", (10, display_frame.shape[0] - 20),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            
                            print(f"FPS: {fps} | Objects: {len(current_detections)} | "
                                  f"Sound: {'ON' if has_detections else 'OFF'}")
                            
                            fps_counter = 0
                            fps_timer = time.time()

                        cv2.imshow("Detection System", display_frame)

                    # Handle exit
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break

            finally:
                processor.stop()
                if DISPLAY_OUTPUT:
                    cv2.destroyAllWindows()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if sound_enabled:
            pygame.mixer.quit()
            pygame.quit()
        print("System shutdown complete.")

if __name__ == '__main__':
    main() 