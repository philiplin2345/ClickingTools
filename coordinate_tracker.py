import keyboard
import pyautogui
import time
import random
import numpy as np
import cv2
import tkinter as tk
from tkinter import ttk

class CoordinateTracker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Coordinate Tracker")
        self.root.geometry("400x600")  # Made the window longer

        self.start_button = ttk.Button(self.root, text="Start", command=self.start_tracking)
        self.start_button.pack(pady=10)

        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.coordinates_frame = ttk.Frame(self.root)
        self.coordinates_frame.pack(pady=10)

        self.first_click_label = ttk.Label(self.coordinates_frame, text="First click: Not set")
        self.first_click_label.pack()

        self.second_click_label = ttk.Label(self.coordinates_frame, text="Second click: Not set")
        self.second_click_label.pack()

        self.areas_frame = ttk.Frame(self.root)
        self.areas_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.areas_label = ttk.Label(self.areas_frame, text="Tracked Areas:")
        self.areas_label.pack()

        self.areas_listbox = tk.Listbox(self.areas_frame)
        self.areas_listbox.pack(fill=tk.BOTH, expand=True)

        self.is_tracking = False
        self.first_click = None
        self.second_click = None
        self.areas = []

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_tracking(self):
        self.is_tracking = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        keyboard.on_press(self.on_key_press)

    def stop_tracking(self):
        self.is_tracking = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        keyboard.unhook_all()
        self.first_click = None
        self.second_click = None
        self.first_click_label.config(text="First click: Not set")
        self.second_click_label.config(text="Second click: Not set")

    def on_key_press(self, event):
        if event.name == 'f9' and self.is_tracking:
            x, y = pyautogui.position()
            self.handle_click(x, y)

    def handle_click(self, x, y):
        if not self.first_click or (x <= self.first_click[0] and y <= self.first_click[1]):
            self.first_click = (x, y)
            self.second_click = None
            self.first_click_label.config(text=f"First click: ({x}, {y})")
            self.second_click_label.config(text="Second click: Not set")
        elif not self.second_click:
            self.second_click = (x, y)
            self.second_click_label.config(text=f"Second click: ({x}, {y})")
            
            # Add the area to the list
            self.areas.append({
                'x1': self.first_click[0],
                'y1': self.first_click[1],
                'x2': self.second_click[0],
                'y2': self.second_click[1]
            })
            self.update_area_list()

            # Reset for the next area
            self.first_click = None
            self.second_click = None
            self.first_click_label.config(text="First click: Not set")
            self.second_click_label.config(text="Second click: Not set")

    def update_area_list(self):
        self.areas_listbox.delete(0, tk.END)
        for i, area in enumerate(self.areas):
            self.areas_listbox.insert(tk.END, f"Area {i+1}: ({area['x1']}, {area['y1']}, {area['x2']}, {area['y2']})")

    def on_closing(self):
        keyboard.unhook_all()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    tracker = CoordinateTracker()
    tracker.run()