import keyboard
import pyautogui
import time
import random
import numpy as np
import cv2
import functools
from threading import Lock

# Previous area definitions remain the same
clicking_areas={
    "inventory_tag":(1957,873,1984,906),
    "prayer_tag":(2056,874,2083,909),
    "magic_tag":(2105,876,2136,905),
    "spec":(1931,251, 1952,272),
    "prot_mage":"images\protect_from_mage.png",
    "prot_range":"images\protect_from_range.png",
    "prot_melee":"images\protect_from_melee.png",
    "sgs":"images/sgs.png"
}
searching_areas={
    "prayers":(1888,1101,2054,1152),
    "inventory": (1841, 928,2092, 1039)
}
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
pyautogui.PAUSE=0.05
last_execution_time = 0
execution_lock = Lock()
MIN_DELAY = 0.2  # Minimum delay in seconds

def timing_decorator(func):
    @functools.wraps(func)  # Preserve the original function's metadata
    def wrapper(*args, **kwargs):
        start_time = time.time()  # Record the start time
        result = func(*args, **kwargs)  # Call the original function
        end_time = time.time()  # Record the end time
        execution_time = end_time - start_time  # Calculate execution time
        print(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds.")
        return result  # Return the result of the function
    return wrapper

def throttle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global last_execution_time
        with execution_lock:
            current_time = time.time()
            time_since_last_execution = current_time - last_execution_time
            if time_since_last_execution < MIN_DELAY:
                time.sleep(MIN_DELAY - time_since_last_execution)
            result = func(*args, **kwargs)
            last_execution_time = time.time()
        return result
    return wrapper

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

# def weighted_random_point_in_area(area, center_weight=0.7):
#     x_min, y_min, x_max, y_max = area
#     center_x, center_y = (x_min + x_max) / 2, (y_min + y_max) / 2
#     width, height = x_max - x_min, y_max - y_min

#     # Generate a point using a uniform distribution, then apply weighting
#     x = random.uniform(x_min, x_max)
#     y = random.uniform(y_min, y_max)

#     # Apply weighting towards the center
#     x = int(x * (1 - center_weight) + center_x * center_weight)
#     y = int(y * (1 - center_weight) + center_y * center_weight)

#     return (x, y)


def click_spot(area):
    spot = weighted_random_point_in_area(area)
    pyautogui.click(spot[0], spot[1])
    # time.sleep(random.uniform(0.1, 0.5))

def click_spots(areas):
    for area in areas:
        spot = weighted_random_point_in_area(area)
        pyautogui.click(spot[0], spot[1])
        time.sleep(random.uniform(0.1, 0.5))


@timing_decorator
# @throttle
def on_f5_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.1))
        find_and_click_image(clicking_areas["prot_mage"],searching_areas["prayers"])
        click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f6_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.1))
        find_and_click_image(clicking_areas["prot_range"],searching_areas["prayers"])
        click_spot(clicking_areas["inventory_tag"])


@timing_decorator
# @throttle
def on_f7_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["prayer_tag"])
        time.sleep(random.uniform(0.05, 0.1))
        find_and_click_image(clicking_areas["prot_melee"],searching_areas["prayers"])
        click_spot(clicking_areas["inventory_tag"])

@timing_decorator
# @throttle
def on_f8_press(e):
    if e.event_type == keyboard.KEY_DOWN:
        click_spot(clicking_areas["inventory_tag"])
        time.sleep(random.uniform(0.05, 0.1))
        find_and_click_image(clicking_areas["sgs"],searching_areas["inventory"])
        time.sleep(random.uniform(0.7, 0.8))
        click_spot(clicking_areas["spec"])
        
# Define the search area for the image (x_min, y_min, x_max, y_max)
SEARCH_AREA = (500, 300, 1000, 600)  # Adjust these coordinates as needed

@timing_decorator
def find_and_click_image(image_path,search_area):
    start_time = time.time()
    
    # Take a screenshot of only the search area
    x_min, y_min, x_max, y_max = search_area
    screenshot = pyautogui.screenshot(region=(x_min, y_min, x_max - x_min, y_max - y_min))
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    before_read_time = time.time()
    # Read the template image
    template = cv2.imread(image_path, 0)
    after_read_time = time.time()
    # Perform template matching
    result = cv2.matchTemplate(cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    match_time = time.time()
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

        # Move the mouse to the point (this initiates the hover)
        pyautogui.moveTo(click_x, click_y)
        
        # Wait for 0.05 seconds
        time.sleep(random.uniform(0.11, 0.125))

        pre_click_time = time.time()
        # Click on the weighted random point
        pyautogui.click(click_x, click_y)
        
        end_time = time.time()
        print(f"Image found and clicked in {(end_time - start_time) * 1000:.2f} ms. max_val is {max_val}. start-before = {before_read_time-start_time} imageread= {after_read_time-before_read_time} matchtime {match_time -after_read_time} click time = {end_time-pre_click_time} end-after {end_time-after_read_time}")
    else:
        print(f"Image not found in the search area max value is {max_val}")

# Set up the listeners for F5, F6, F7, and F8 keys
keyboard.on_press_key("f5", on_f5_press)
keyboard.on_press_key("f6", on_f6_press)
keyboard.on_press_key("f7", on_f7_press)
keyboard.on_press_key("f8", on_f8_press)

print("Listening for F5, F6, F7, and F8 key presses. Press Ctrl+C to exit.")

# Keep the script running
keyboard.wait()