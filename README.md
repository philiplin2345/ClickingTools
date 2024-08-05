# ClickingTools

## Overview

This project contains Python scripts that automate mouse clicks based on keyboard inputs and image detection. It's designed to perform the following functions:

1. Click at random points within predefined screen areas when F5, F6, or F7 keys are pressed.
2. Detect a specific image on the screen and click its center when F8 is pressed.
3. Provide a utility to visually determine screen coordinates for defining click areas.

## Features

- **Multi-key Support**: Separate functions for F5, F6, and F7 keys, each clicking in different predefined areas.
- **Randomized Clicks**: Clicks occur at random points within specified areas.
- **Variable Delays**: Random delays between clicks to simulate human behavior.
- **Image Detection**: Ability to find and click on a specific image on the screen.
- **Coordinate Tracker**: A separate utility to help users visually define click areas.
- **Weighted Random Clicks**: Clicks are more likely to occur near the center of defined areas or detected images, with decreasing probability towards the edges.
- **Optimized Image Detection**: Searches for images within a predefined area for improved performance.

## Files

1. `auto_clicker.py`: Main script for auto-clicking and image detection.
2. `coordinate_tracker.py`: Utility for visually determining screen coordinates.

## Dependencies

- Python 3.6+
- pyautogui
- keyboard
- opencv-python
- numpy
- pynput (for coordinate tracker)

## Setup

1. Clone this repository:
```
git clone https://github.com/yourusername/auto-clicker.git
cd auto-clicker
```
2. Install the required dependencies:

`pip install pyautogui keyboard opencv-python numpy pynput`

3. In `auto_clicker.py`, update the `IMAGE_PATH` variable with the path to the image you want to detect.

4. Adjust the predefined areas (`areas_set1`, `areas_set2`, `areas_set3`) in `auto_clicker.py` according to your needs. You can use the `coordinate_tracker.py` utility to help determine these areas.

5. Adjust the `SEARCH_AREA` constant in `auto_clicker.py` to define where the script should look for the image when F8 is pressed.

## Usage

### Auto Clicker and Image Detection

Run the main script:

`main.py`

- Press F5, F6, or F7 to trigger clicks in the corresponding predefined areas.
- Press F8 to detect the specified image on screen and click its center.
- Press Ctrl+C in the terminal to exit the script.

### Coordinate Tracker

Run the coordinate tracker utility:
`python coordinate_tracker.py`

- Click "Start Tracking" to begin tracking mouse movements.
- Left-click to set the top-left corner of an area, then left-click again to set the bottom-right corner.
- Use the displayed coordinates to update the areas in `auto_clicker.py`.

## Customization

- Modify the click areas in `auto_clicker.py` to suit your needs.
- Adjust the random delay range in the `click_spots` function.
- Change the confidence threshold for image detection in the `find_and_click_image` function.
- Adjust the `center_weight` parameter in the `weighted_random_point_in_area` function to control how strongly clicks favor the center of areas.
- Modify the `SEARCH_AREA` constant in the script to define where the image detection should occur.

## Notes

- This script requires administrative privileges to listen for global key presses.
- Be cautious when using auto-clickers, as they may violate terms of service for some applications or websites.
- The image detection feature's performance may vary based on system specifications and screen resolution.

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to check [issues page](https://github.com/yourusername/auto-clicker/issues) if you want to contribute.

## License

[MIT License](https://choosealicense.com/licenses/mit/)