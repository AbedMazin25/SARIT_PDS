#!/usr/bin/env python3
"""
Watchdog Service for Integrated OAK-D Detection System

This script runs the integrated detection system and automatically restarts it
if it terminates unexpectedly. It acts as a service daemon to ensure the 
detection system stays running continuously.
"""

import subprocess
import time
import signal
import sys
import os
import logging
import argparse
from datetime import datetime
from pathlib import Path

class DetectionSystemWatchdog:
    def __init__(self, script_path, camera_only=True, restart_delay=5, max_restarts=None):
        """
        Initialize the watchdog service
        
        Args:
            script_path: Path to the run_integrated_detection_system.sh script
            camera_only: Run camera only mode (ignore emulator)
            restart_delay: Seconds to wait before restarting
            max_restarts: Maximum number of restarts (None for unlimited)
        """
        self.script_path = Path(script_path)
        self.camera_only = camera_only
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts
        
        self.running = True
        self.process = None
        self.restart_count = 0
        self.start_time = None
        
        # Setup logging
        self.setup_logging()
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("Watchdog service initialized")
        self.logger.info(f"Target script: {self.script_path}")
        self.logger.info(f"Camera only mode: {self.camera_only}")
        self.logger.info(f"Restart delay: {self.restart_delay}s")
        self.logger.info(f"Max restarts: {self.max_restarts or 'unlimited'}")
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Setup logging
        log_file = log_dir / f"watchdog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.stop_process()
    
    def build_command(self):
        """Build the command to run the detection system"""
        cmd = [str(self.script_path)]
        
        if self.camera_only:
            cmd.append("--camera-only")
            
        return cmd
    
    def start_process(self):
        """Start the detection system process"""
        try:
            cmd = self.build_command()
            self.logger.info(f"Starting detection system: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.start_time = time.time()
            self.logger.info(f"Detection system started with PID: {self.process.pid}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start detection system: {e}")
            return False
    
    def stop_process(self):
        """Stop the detection system process"""
        if self.process:
            try:
                self.logger.info(f"Stopping detection system (PID: {self.process.pid})...")
                
                # Send SIGTERM first
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop gracefully
                    self.logger.warning("Process didn't stop gracefully, force killing...")
                    self.process.kill()
                    self.process.wait()
                
                self.logger.info("Detection system stopped")
                
            except Exception as e:
                self.logger.error(f"Error stopping process: {e}")
            
            finally:
                self.process = None
    
    def monitor_process(self):
        """Monitor the running process and handle output"""
        if not self.process:
            return False
        
        # Check if process is still running
        if self.process.poll() is not None:
            # Process has terminated
            return_code = self.process.returncode
            runtime = time.time() - self.start_time if self.start_time else 0
            
            self.logger.warning(f"Detection system terminated with code {return_code} after {runtime:.1f}s")
            
            # Log any remaining output
            try:
                output, _ = self.process.communicate(timeout=1)
                if output:
                    self.logger.info(f"Final output: {output.strip()}")
            except:
                pass
            
            self.process = None
            return False
        
        # Process is still running - log any output
        try:
            # Non-blocking read of output
            import select
            if select.select([self.process.stdout], [], [], 0.1)[0]:
                line = self.process.stdout.readline()
                if line:
                    self.logger.info(f"Detection: {line.strip()}")
        except:
            pass  # Ignore read errors
        
        return True
    
    def should_restart(self):
        """Check if we should restart the process"""
        if not self.running:
            return False
            
        # For the initial start, allow it even if max_restarts is 1 (test mode)
        if self.restart_count == 0:
            return True
            
        if self.max_restarts is not None and self.restart_count >= self.max_restarts:
            self.logger.error(f"Maximum restart limit ({self.max_restarts}) reached")
            return False
            
        return True
    
    def run(self):
        """Main watchdog loop"""
        self.logger.info("Starting watchdog service...")
        
        while self.running:
            try:
                # Start the process if not running
                if not self.process:
                    if not self.should_restart():
                        break
                        
                    if self.restart_count > 0:
                        self.logger.info(f"Waiting {self.restart_delay}s before restart #{self.restart_count + 1}...")
                        time.sleep(self.restart_delay)
                    
                    if self.start_process():
                        self.restart_count += 1
                    else:
                        self.logger.error("Failed to start process, waiting before retry...")
                        time.sleep(self.restart_delay)
                        continue
                
                # Monitor the process
                if not self.monitor_process():
                    # Process terminated, it will be restarted in next loop iteration
                    continue
                
                # Small delay to prevent busy waiting
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in watchdog loop: {e}")
                time.sleep(1)
        
        # Cleanup
        self.stop_process()
        self.logger.info("Watchdog service stopped")

def main():
    parser = argparse.ArgumentParser(description='Watchdog service for OAK-D Detection System')
    
    parser.add_argument('--script-path', '-s', 
                       default='./run_integrated_detection_system.sh',
                       help='Path to the detection system script')
    
    parser.add_argument('--no-camera-only', action='store_true',
                       help='Allow emulator (disable camera-only mode)')
    
    parser.add_argument('--restart-delay', '-d', type=int, default=5,
                       help='Delay in seconds before restarting (default: 5)')
    
    parser.add_argument('--max-restarts', '-m', type=int,
                       help='Maximum number of restarts (default: unlimited)')
    
    parser.add_argument('--test', action='store_true',
                       help='Test mode - start once and exit')
    
    args = parser.parse_args()
    
    # Resolve script path
    script_path = Path(args.script_path).resolve()
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    # Create and run watchdog
    watchdog = DetectionSystemWatchdog(
        script_path=script_path,
        camera_only=not args.no_camera_only,
        restart_delay=args.restart_delay,
        max_restarts=args.max_restarts if not args.test else 1
    )
    
    try:
        watchdog.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 