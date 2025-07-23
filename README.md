# OAK-D Detection System Watchdog Service

This directory contains a watchdog service system that automatically starts and monitors the OAK-D detection system, ensuring it stays running continuously and automatically restarts if it terminates unexpectedly.

## Files

- `watchdog_service.py` - Main watchdog script that monitors and restarts the detection system
- `oak-detection.service` - Systemd service file for automatic startup
- `service_manager.sh` - Helper script for managing the service
- `run_integrated_detection_system.sh` - The main detection system script (monitored by watchdog)

## Quick Start

### 1. Install the Service (Run at Startup)

```bash
# Install and enable the service to start automatically at boot
./service_manager.sh install

# Start the service immediately
./service_manager.sh start
```

### 2. Manual Watchdog Operation

```bash
# Run the watchdog manually (camera-only mode, ignoring emulator)
python3 watchdog_service.py

# Run with custom settings
python3 watchdog_service.py --restart-delay 10 --max-restarts 5

# Test mode (start once and exit)
python3 watchdog_service.py --test
```

## Service Management Commands

```bash
# Service control
./service_manager.sh start      # Start the service
./service_manager.sh stop       # Stop the service
./service_manager.sh restart    # Restart the service
./service_manager.sh status     # Show service status

# Installation
./service_manager.sh install    # Install and enable service
./service_manager.sh uninstall  # Remove service

# Auto-start control
./service_manager.sh enable     # Enable auto-start at boot
./service_manager.sh disable    # Disable auto-start

# Monitoring
./service_manager.sh logs       # View live logs
```

## Watchdog Options

The watchdog service supports several command-line options:

```bash
python3 watchdog_service.py [options]

Options:
  -s, --script-path PATH     Path to detection system script
  --no-camera-only          Allow emulator (disable camera-only mode)
  -d, --restart-delay N      Delay in seconds before restarting (default: 5)
  -m, --max-restarts N       Maximum number of restarts (default: unlimited)
  --test                     Test mode - start once and exit
```

## How It Works

1. **Watchdog Process**: Continuously monitors the detection system process
2. **Automatic Restart**: If the detection system terminates, waits a few seconds and restarts it
3. **Logging**: All activity is logged to both console and log files in the `logs/` directory
4. **Signal Handling**: Properly handles shutdown signals for clean termination
5. **Service Integration**: Can run as a systemd service for automatic startup

## Default Behavior

- **Camera-only mode**: Ignores the warning emulator (as requested)
- **Automatic restart**: Unlimited restarts with 5-second delay between attempts
- **Logging**: Creates timestamped log files in `logs/` directory
- **Clean shutdown**: Handles Ctrl+C and system signals gracefully

## Logs

- Service logs: `journalctl -u oak-detection -f`
- Watchdog logs: `logs/watchdog_YYYYMMDD_HHMMSS.log`
- Detection system output is captured and logged by the watchdog

## Troubleshooting

### Service Won't Start
```bash
# Check service status
./service_manager.sh status

# View detailed logs
./service_manager.sh logs
```

### Manual Testing
```bash
# Test the detection system directly
./run_integrated_detection_system.sh --camera-only

# Test the watchdog manually
python3 watchdog_service.py --test
```

### Reset Service
```bash
# Completely reset the service
./service_manager.sh uninstall
./service_manager.sh install
./service_manager.sh start
```

## Development Notes

- The watchdog runs the detection system in camera-only mode by default
- All process output is captured and logged
- The service runs as the user 'ods' with appropriate environment variables
- Systemd automatically restarts the watchdog if it crashes
- The watchdog then restarts the detection system if it terminates

## Example Usage

```bash
# Set up for production use (starts at boot)
./service_manager.sh install
./service_manager.sh start

# Monitor the system
./service_manager.sh logs

# Stop for maintenance
./service_manager.sh stop

# Restart after updates
./service_manager.sh restart
``` 