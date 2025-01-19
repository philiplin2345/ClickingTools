from pynput import mouse, keyboard
import time
import random
import threading
from screeninfo import get_monitors
import pyautogui  # For more reliable mouse control

class ClickRecorder:
    def __init__(self):
        self.clicks = []
        self.recording = False
        self.playing = False
        self.start_time = 0
        self.stop_replay = False
        self.num_loops = 3
        
        # Get primary monitor
        self.monitor = get_monitors()[0]
        
        # Listeners
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        
        # Start listeners
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        # Set up pyautogui safety net
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01  # Minimum time between actions

    def on_press(self, key):
        try:
            if key == keyboard.Key.f1:
                if not self.recording:
                    print("Recording started...")
                    self.clicks = []
                    self.recording = True
                    self.start_time = time.time()
                else:
                    print("Recording stopped...")
                    self.recording = False
                    
            elif key == keyboard.Key.f2:
                if not self.recording:
                    if not self.playing:
                        print("Replaying clicks...")
                        self.stop_replay = False
                        self.replay_clicks()
                    else:
                        print("Stopping replay...")
                        self.stop_replay = True
                
        except AttributeError:
            pass

    def on_click(self, x, y, button, pressed):
        if self.recording and pressed:
            current_time = time.time()
            if len(self.clicks) == 0:
                delay = 0
            else:
                delay = current_time - self.start_time - self.clicks[-1][2]
            self.clicks.append((x, y, current_time - self.start_time, button))
            print(f"Recorded {button} click at ({x}, {y})")

    def replay_clicks(self):
        if self.playing:
            return
            
        self.playing = True
        thread = threading.Thread(target=self._replay)
        thread.start()

    def _replay(self):
        try:
            loop_count = 0
            while loop_count < self.num_loops and not self.stop_replay:
                previous_time = 0
                
                for i, (x, y, timestamp, button) in enumerate(self.clicks):
                    if self.stop_replay:
                        break
                        
                    # Calculate delay
                    delay = timestamp - previous_time
                    delay = delay * random.uniform(0.9, 1.1)
                    
                    time.sleep(delay)
                    
                    # Add random variance to position (±5 pixels)
                    random_x = int(x + random.uniform(-2, 2))
                    random_y = int(y + random.uniform(-2, 2))
                    
                    # Ensure coordinates are within screen bounds
                    random_x = max(0, min(random_x, self.monitor.width - 1))
                    random_y = max(0, min(random_y, self.monitor.height - 1))
                    
                    try:
                        # Move mouse
                        pyautogui.moveTo(random_x, random_y)
                        time.sleep(random.uniform(0.11, 0.125))
                        # Click based on button type
                        if button == mouse.Button.left:
                            pyautogui.click(button='left')
                        elif button == mouse.Button.right:
                            pyautogui.click(button='right')
                            
                        print(f"Clicked at ({random_x}, {random_y})")
                    except Exception as e:
                        print(f"Click failed: {e}")
                    
                    previous_time = timestamp
                time.sleep(random.uniform(0.11, 0.125))
                loop_count += 1
                print(f"Completed loop {loop_count} of {self.num_loops}")
                
        finally:
            self.playing = False
            self.stop_replay = False
            print("Replay stopped")

def get_num_loops():
    while True:
        try:
            loops = int(input("Enter number of loops to replay (default is 3): ").strip())
            if loops > 0:
                return loops
            print("Please enter a positive number")
        except ValueError:
            print("Please enter a valid number")

if __name__ == "__main__":
    print("Installing required packages if needed...")
    import subprocess
    import sys
    
    # Install required packages
    required_packages = ['pyautogui', 'screeninfo']
    for package in required_packages:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    recorder = ClickRecorder()
    recorder.num_loops = 1970
    print("\nPress F1 to start/stop recording")
    print("Press F2 to start/stop replay")
    print("Recording both left and right clicks...")
    
    # Keep the program running
    while True:
        time.sleep(1)