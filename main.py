import keyboard
import pyautogui
import time
import random
import numpy as np
import cv2

# Previous area definitions remain the same
areas_set1 = [
    (50, 50, 150, 150),
    (200, 200, 300, 300),
    (350, 350, 450, 450)
]

areas_set2 = [
    (500, 50, 600, 150),
    (650, 200, 750, 300),
    (800, 350, 900, 450)
]

areas_set3 = [
    (950, 50, 1050, 150),
    (1100, 200, 1200, 300),
    (1250, 350, 1350, 450)
]

IMAGE_PATH = 'path/to/your/image.png'

def weighted_random_point_in_area(area, center_weight=0.7):
    x_min, y_min, x_max, y_max = area
    center_x, center_y = (x_min + x_max) / 2, (y_min + y_max) / 2
    width, height = x_max - x_min, y_max - y_min
    
    while True:
        # Generate a point using a normal distribution
        x = int(random.gauss(center_x, width * (1 - center_weight) / 2))
        y = int(random.gauss(center_y, height * (1 - center_weight) / 2))
        
        # Check if the point is within the area
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return (x, y)

def click_spots(areas):
    for area in areas:
        spot = weighted_random_point_in_area(area)
        pyautogui.click(spot[0], spot[1])
        time.sleep(random.uniform(0.1, 0.5))

def on_f5_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spots(areas_set1)

def on_f6_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spots(areas_set2)

def on_f7_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spots(areas_set3)
# Define the search area for the image (x_min, y_min, x_max, y_max)
SEARCH_AREA = (500, 300, 1000, 600)  # Adjust these coordinates as needed

def find_and_click_image(e):
    if e.event_type == keyboard.KEY_DOWN:
        start_time = time.time()
        
        # Take a screenshot of only the search area
        x_min, y_min, x_max, y_max = SEARCH_AREA
        screenshot = pyautogui.screenshot(region=(x_min, y_min, x_max - x_min, y_max - y_min))
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Read the template image
        template = cv2.imread(IMAGE_PATH, 0)
        
        # Perform template matching
        result = cv2.matchTemplate(cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # If the image is found (you can adjust the threshold)
        if max_val > 0.8:
            # Calculate the center and dimensions of the found image
            h, w = template.shape
            center_x = x_min + max_loc[0] + w // 2
            center_y = y_min + max_loc[1] + h // 2
            
            # Define the area of the found image
            image_area = (x_min + max_loc[0], y_min + max_loc[1], 
                          x_min + max_loc[0] + w, y_min + max_loc[1] + h)
            
            # Get a weighted random point within the image area
            click_x, click_y = weighted_random_point_in_area(image_area)
            
            # Click on the weighted random point
            pyautogui.click(click_x, click_y)
            
            end_time = time.time()
            print(f"Image found and clicked in {(end_time - start_time) * 1000:.2f} ms")
        else:
            print("Image not found in the search area")

# Set up the listeners for F5, F6, F7, and F8 keys
keyboard.on_press_key("f5", on_f5_press)
keyboard.on_press_key("f6", on_f6_press)
keyboard.on_press_key("f7", on_f7_press)
keyboard.on_press_key("f8", find_and_click_image)

print("Listening for F5, F6, F7, and F8 key presses. Press Ctrl+C to exit.")

# Keep the script running
keyboard.wait()