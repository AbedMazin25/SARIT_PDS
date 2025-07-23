#!/bin/bash
# Service Manager for OAK-D Detection System
# Manages the watchdog service installation and control

set -e

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SERVICE_NAME="oak-detection"
SERVICE_FILE="$DIR/${SERVICE_NAME}.service"
SYSTEM_SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# Function to display usage
usage() {
    echo "Usage: $0 {install|uninstall|start|stop|restart|status|enable|disable|logs}"
    echo ""
    echo "Service Manager for OAK-D Detection System Watchdog"
    echo ""
    echo "Commands:"
    echo "  install     Install the service (requires sudo)"
    echo "  uninstall   Remove the service (requires sudo)"
    echo "  start       Start the service"
    echo "  stop        Stop the service"
    echo "  restart     Restart the service"
    echo "  status      Show service status"
    echo "  enable      Enable service to start at boot"
    echo "  disable     Disable service auto-start"
    echo "  logs        Show service logs"
    echo ""
    echo "Examples:"
    echo "  $0 install      # Install and enable the service"
    echo "  $0 start        # Start the detection system"
    echo "  $0 logs         # View live logs"
    echo ""
    exit 1
}

# Check if service file exists
check_service_file() {
    if [[ ! -f "$SERVICE_FILE" ]]; then
        echo "Error: Service file not found: $SERVICE_FILE"
        exit 1
    fi
}

# Install the service
install_service() {
    echo "Installing OAK-D Detection System service..."
    
    check_service_file
    
    # Copy service file to systemd directory
    sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE_PATH"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable the service
    sudo systemctl enable "$SERVICE_NAME"
    
    echo "Service installed and enabled successfully!"
    echo "Use '$0 start' to start the service"
}

# Uninstall the service
uninstall_service() {
    echo "Uninstalling OAK-D Detection System service..."
    
    # Stop the service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    # Disable the service
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        sudo systemctl disable "$SERVICE_NAME"
    fi
    
    # Remove service file
    if [[ -f "$SYSTEM_SERVICE_PATH" ]]; then
        sudo rm "$SYSTEM_SERVICE_PATH"
    fi
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    echo "Service uninstalled successfully!"
}

# Start the service
start_service() {
    echo "Starting OAK-D Detection System service..."
    sudo systemctl start "$SERVICE_NAME"
    echo "Service started!"
    echo "Use '$0 status' to check status or '$0 logs' to view logs"
}

# Stop the service
stop_service() {
    echo "Stopping OAK-D Detection System service..."
    sudo systemctl stop "$SERVICE_NAME"
    echo "Service stopped!"
}

# Restart the service
restart_service() {
    echo "Restarting OAK-D Detection System service..."
    sudo systemctl restart "$SERVICE_NAME"
    echo "Service restarted!"
}

# Show service status
show_status() {
    echo "=== OAK-D Detection System Service Status ==="
    systemctl status "$SERVICE_NAME" || true
    echo ""
    echo "Service file: $SYSTEM_SERVICE_PATH"
    echo "Logs: journalctl -u $SERVICE_NAME -f"
}

# Enable service auto-start
enable_service() {
    echo "Enabling OAK-D Detection System service auto-start..."
    sudo systemctl enable "$SERVICE_NAME"
    echo "Service enabled for auto-start at boot!"
}

# Disable service auto-start
disable_service() {
    echo "Disabling OAK-D Detection System service auto-start..."
    sudo systemctl disable "$SERVICE_NAME"
    echo "Service disabled from auto-start!"
}

# Show logs
show_logs() {
    echo "=== OAK-D Detection System Service Logs ==="
    echo "Press Ctrl+C to exit log view"
    echo ""
    journalctl -u "$SERVICE_NAME" -f
}

# Check if we have the right permissions
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        echo "Warning: Running as root. This script should be run as a regular user."
        echo "sudo will be used automatically for operations that require it."
    fi
}

# Main logic
case "${1:-}" in
    install)
        check_permissions
        install_service
        ;;
    uninstall)
        check_permissions
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    enable)
        enable_service
        ;;
    disable)
        disable_service
        ;;
    logs)
        show_logs
        ;;
    *)
        usage
        ;;
esac 