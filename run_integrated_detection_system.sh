#!/bin/bash
# Integrated OAK-D Detection System Runner
# Combines object detection, depth measurement, UVC output, and alarm systems

# Exit on error
set -e

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Function to display usage information
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Integrated OAK-D Detection System with Proximity Warnings"
    echo "Combines object detection, depth measurement, UVC output, and alarm systems."
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -d, --demo          Run emulator in demo mode (no camera needed)"
    echo "  -e, --emulator-only Run only the emulator in demo mode"
    echo "  -c, --camera-only   Run only the camera processing (no emulator)"
    echo "  -u, --uvc-only      Run only UVC output (no detection display)"
    echo "  -n, --no-display    Run without visual display (headless mode)"
    echo "  -s, --no-sound      Disable sound alerts"
    echo "  --flash-bootloader  Flash bootloader to device"
    echo "  --flash-app         Flash application to device"
    echo "  --load-and-exit     Load UVC application and exit"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run full system with detection, alarms, and emulator"
    echo "  $0 -d               # Demo mode with simulated danger levels"
    echo "  $0 -c -s            # Camera only without sound"
    echo "  $0 -u               # UVC output only for external applications"
    echo "  $0 --headless       # Headless operation (no display)"
    echo ""
    exit 1
}

# Default values
DEMO_MODE=false
EMULATOR_ONLY=false
CAMERA_ONLY=false
UVC_ONLY=false
NO_DISPLAY=false
NO_SOUND=false
FLASH_BOOTLOADER=false
FLASH_APP=false
LOAD_AND_EXIT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -d|--demo)
            DEMO_MODE=true
            shift
            ;;
        -e|--emulator-only)
            EMULATOR_ONLY=true
            shift
            ;;
        -c|--camera-only)
            CAMERA_ONLY=true
            shift
            ;;
        -u|--uvc-only)
            UVC_ONLY=true
            shift
            ;;
        -n|--no-display|--headless)
            NO_DISPLAY=true
            shift
            ;;
        -s|--no-sound)
            NO_SOUND=true
            shift
            ;;
        --flash-bootloader)
            FLASH_BOOTLOADER=true
            shift
            ;;
        --flash-app)
            FLASH_APP=true
            shift
            ;;
        --load-and-exit)
            LOAD_AND_EXIT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check for conflicting options
if $EMULATOR_ONLY && ($CAMERA_ONLY || $UVC_ONLY); then
    echo "Error: Cannot use --emulator-only with camera options"
    exit 1
fi

if $UVC_ONLY && $CAMERA_ONLY; then
    echo "Error: Cannot use --uvc-only and --camera-only together"
    exit 1
fi

# Install required dependencies if needed
check_dependencies() {
    echo "Checking dependencies..."
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 not found. Please install Python 3."
        exit 1
    fi
    
    # Check for required Python packages
    local missing_packages=()
    
    # Always check for basic packages
    if ! python3 -c "import numpy" &> /dev/null; then
        missing_packages+=("numpy")
    fi
    
    if ! python3 -c "import cv2" &> /dev/null; then
        missing_packages+=("opencv-python")
    fi
    
    # Check for pygame (for sound)
    if ! $NO_SOUND && ! python3 -c "import pygame" &> /dev/null; then
        missing_packages+=("pygame")
    fi
    
    # Check for DepthAI (for camera operations)
    if ! $EMULATOR_ONLY && ! python3 -c "import depthai" &> /dev/null; then
        missing_packages+=("depthai")
    fi
    
    # Check for jetson-inference (if available)
    if ! $EMULATOR_ONLY && ! python3 -c "import jetson_inference" &> /dev/null; then
        echo "Warning: jetson-inference not found. This is required for object detection."
        echo "Please install jetson-inference from: https://github.com/dusty-nv/jetson-inference"
        exit 1
    fi
    
    # Install missing packages
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo "Installing missing packages: ${missing_packages[*]}"
        pip3 install "${missing_packages[@]}"
    fi
    
    echo "All dependencies verified."
}

# Cleanup function
cleanup() {
    # Kill any background processes
    if [ -n "$EMULATOR_PID" ]; then
        echo "Stopping emulator (PID: $EMULATOR_PID)..."
        kill $EMULATOR_PID 2>/dev/null || true
    fi
    
    echo "System shutdown complete."
}

# Register cleanup function on exit
trap cleanup EXIT

# Check dependencies
check_dependencies

# Verify sound files exist
if ! $NO_SOUND && ! $EMULATOR_ONLY; then
    if [ ! -f "$DIR/sounds/low warning user.mp3" ] || [ ! -f "$DIR/sounds/high warning sound.mp3" ]; then
        echo "Warning: Sound files not found in $DIR/sounds/"
        echo "Sound alerts will be disabled."
        NO_SOUND=true
    fi
fi

# Build command line arguments for the integrated system
build_camera_args() {
    local args=""
    
    if $FLASH_BOOTLOADER; then
        args="$args --flash-bootloader"
    fi
    
    if $FLASH_APP; then
        args="$args --flash-app"
    fi
    
    if $LOAD_AND_EXIT; then
        args="$args --load-and-exit"
    fi
    
    if $UVC_ONLY; then
        args="$args --uvc-only"
    fi
    
    if $NO_SOUND; then
        args="$args --no-sound"
    fi
    
    if $CAMERA_ONLY; then
        args="$args --no-emulator"
    fi
    
    if $NO_DISPLAY; then
        args="$args --headless"
    fi
    
    echo "$args"
}

# Print system information
print_system_info() {
    echo ""
    echo "=================================================================="
    echo "INTEGRATED OAK-D DETECTION SYSTEM"
    echo "=================================================================="
    echo "Date: $(date)"
    echo "System: $(uname -a)"
    echo "Python: $(python3 --version)"
    echo "Working Directory: $DIR"
    echo ""
    echo "Configuration:"
    echo "• Detection Model: ssd-mobilenet-v2"
    echo "• Sound Alerts: $(if $NO_SOUND; then echo 'DISABLED'; else echo 'ENABLED'; fi)"
    echo "• Visual Display: $(if $NO_DISPLAY; then echo 'DISABLED'; else echo 'ENABLED'; fi)"
    echo "• Emulator Communication: $(if $CAMERA_ONLY; then echo 'DISABLED'; else echo 'ENABLED'; fi)"
    echo "=================================================================="
    echo ""
}

# Run the system based on options
print_system_info

if $EMULATOR_ONLY; then
    echo "Starting emulator in demo mode..."
    python3 "$DIR/proximity_warning_emulator.py" --demo
    
elif $DEMO_MODE; then
    echo "Starting system in demo mode..."
    echo "Starting emulator with simulated danger levels..."
    python3 "$DIR/proximity_warning_emulator.py" --demo &
    EMULATOR_PID=$!
    
    # Give emulator time to start
    sleep 2
    
    echo "Starting camera processing..."
    camera_args=$(build_camera_args)
    python3 "$DIR/combined_detection_depth_uvc.py" $camera_args
    
else
    # Standard operation
    if ! $CAMERA_ONLY; then
        echo "Starting proximity warning emulator..."
        python3 "$DIR/proximity_warning_emulator.py" &
        EMULATOR_PID=$!
        
        # Give emulator time to start
        sleep 2
    fi
    
    echo "Starting integrated detection system..."
    camera_args=$(build_camera_args)
    python3 "$DIR/combined_detection_depth_uvc.py" $camera_args
fi

echo ""
echo "System stopped." 