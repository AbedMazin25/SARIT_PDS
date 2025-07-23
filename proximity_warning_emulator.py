#!/usr/bin/env python3
"""
Proximity Warning System Emulator

This app emulates the hardware LED bar and sound system for the 
OAK-D night vision proximity warning system.
"""

import pygame
import numpy as np
import sys
import time
import threading
import socket
import json
import argparse

# Configuration
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 300
LED_COUNT = 10
LED_HEIGHT = 100
LED_SPACING = 5
LED_START_X = 50
BACKGROUND_COLOR = (20, 20, 20)

# Parse arguments
parser = argparse.ArgumentParser(description='Proximity Warning System Emulator')
parser.add_argument('--demo', action='store_true', help='Run in demo mode with simulated danger levels')
parser.add_argument('--port', type=int, default=5555, help='Port to listen for danger level data')
args = parser.parse_args()

class ProximityWarningEmulator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption("Proximity Warning System Emulator")
        
        # Create window
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Create LED lights
        self.leds = []
        led_width = (WINDOW_WIDTH - 2 * LED_START_X - (LED_COUNT - 1) * LED_SPACING) // LED_COUNT
        
        for i in range(LED_COUNT):
            x = LED_START_X + i * (led_width + LED_SPACING)
            y = (WINDOW_HEIGHT - LED_HEIGHT) // 2
            
            # Gradient color (Green -> Yellow -> Red)
            if i < LED_COUNT // 3:
                # Green
                color = (0, 255, 0)
            elif i < 2 * LED_COUNT // 3:
                # Yellow
                yellow_intensity = (i - LED_COUNT // 3) / (LED_COUNT // 3)
                color = (255 * yellow_intensity, 255, 0)
            else:
                # Red
                red_intensity = (i - 2 * LED_COUNT // 3) / (LED_COUNT // 3)
                color = (255, 255 * (1 - red_intensity), 0)
                
            self.leds.append({
                'rect': pygame.Rect(x, y, led_width, LED_HEIGHT),
                'color': color,
                'on': False
            })
        
        # Create sounds with different frequencies for different danger levels
        # Sound functionality removed - main script will handle all sounds
        # Track which sound is currently playing
        self.current_playing_sound = None
        
        # Demo mode variables
        self.demo_mode = args.demo
        self.current_danger_level = 0
        self.danger_direction = 1  # 1=increasing, -1=decreasing
        
        # Network setup for receiving danger level
        if not self.demo_mode:
            self.setup_network(args.port)
            
    def setup_network(self, port):
        """Setup network socket to receive danger level data"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.socket.settimeout(0.1)  # Non-blocking
        
        # Start thread to receive data
        self.receiver_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receiver_thread.start()
    
    def receive_data(self):
        """Receive danger level data from network"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                if 'danger_level' in message:
                    self.current_danger_level = message['danger_level']
            except socket.timeout:
                # No data received, continue
                pass
            except Exception as e:
                print(f"Error receiving data: {e}")
            
            time.sleep(0.01)
    
    def update_demo_danger(self):
        """Update danger level for demo mode"""
        # In demo mode, we simulate danger levels going up and down
        self.current_danger_level += self.danger_direction * 1
        
        if self.current_danger_level >= 100:
            self.current_danger_level = 100
            self.danger_direction = -1
        elif self.current_danger_level <= 0:
            self.current_danger_level = 0
            self.danger_direction = 1
            # Pause at zero for a moment
            time.sleep(1)
    
    def update_leds(self):
        """Update LED states based on danger level"""
        # Calculate how many LEDs should be lit
        leds_on = int((self.current_danger_level / 100) * LED_COUNT)
        
        # Update LED states
        for i, led in enumerate(self.leds):
            led['on'] = i < leds_on
        
        # Update sound based on danger level
        self.update_sound()
    
    def update_sound(self):
        """
        Sound functionality removed - the main script now handles all sounds
        This function is kept as a placeholder but does nothing
        """
        pass
    
    def draw(self):
        """Draw the interface"""
        # Clear screen
        self.screen.fill(BACKGROUND_COLOR)
        
        # Draw LEDs
        for led in self.leds:
            if led['on']:
                pygame.draw.rect(self.screen, led['color'], led['rect'])
            else:
                pygame.draw.rect(self.screen, (50, 50, 50), led['rect'])
                pygame.draw.rect(self.screen, (30, 30, 30), led['rect'], 1)
        
        # Draw danger level text
        font = pygame.font.SysFont('Arial', 30)
        text = font.render(f"Danger Level: {self.current_danger_level}%", True, (255, 255, 255))
        self.screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT - 50))
        
        # Draw title
        title_font = pygame.font.SysFont('Arial', 24)
        title = title_font.render("Proximity Warning System Emulator", True, (200, 200, 200))
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 20))
        
        # Draw mode indicator
        mode_font = pygame.font.SysFont('Arial', 18)
        mode_text = "Demo Mode" if self.demo_mode else "Network Mode"
        mode = mode_font.render(mode_text, True, (200, 200, 200))
        self.screen.blit(mode, (WINDOW_WIDTH - mode.get_width() - 20, 20))
        
        # Update display
        pygame.display.flip()
    
    def handle_events(self):
        """Handle events (quit, etc.)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def run(self):
        """Main loop"""
        while self.running:
            self.handle_events()
            
            if self.demo_mode:
                self.update_demo_danger()
                
            self.update_leds()
            self.draw()
            self.clock.tick(30)
        
        # Clean up
        pygame.mixer.quit()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    app = ProximityWarningEmulator()
    app.run() 