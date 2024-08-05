import tkinter as tk
from pynput import mouse

class CoordinateTracker:
    def __init__(self, master):
        self.master = master
        self.master.title("Coordinate Tracker")
        self.master.geometry("300x200")
        
        self.coord_label = tk.Label(master, text="Current: (0, 0)")
        self.coord_label.pack(pady=10)
        
        self.area_label = tk.Label(master, text="No area selected")
        self.area_label.pack(pady=10)
        
        self.start_button = tk.Button(master, text="Start Tracking", command=self.start_tracking)
        self.start_button.pack(pady=5)
        
        self.stop_button = tk.Button(master, text="Stop Tracking", command=self.stop_tracking, state=tk.DISABLED)
        self.stop_button.pack(pady=5)
        
        self.clear_button = tk.Button(master, text="Clear Area", command=self.clear_area)
        self.clear_button.pack(pady=5)
        
        self.listener = None
        self.tracking = False
        self.start_pos = None
        self.end_pos = None

    def start_tracking(self):
        self.tracking = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.listener.start()

    def stop_tracking(self):
        self.tracking = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.listener:
            self.listener.stop()

    def on_move(self, x, y):
        self.coord_label.config(text=f"Current: ({x}, {y})")

    def on_click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            if not self.start_pos:
                self.start_pos = (x, y)
                self.area_label.config(text=f"Start: ({x}, {y})")
            else:
                self.end_pos = (x, y)
                self.update_area_label()

    def update_area_label(self):
        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos
            x2, y2 = self.end_pos
            self.area_label.config(text=f"Area: ({min(x1, x2)}, {min(y1, y2)}, {max(x1, x2)}, {max(y1, y2)})")

    def clear_area(self):
        self.start_pos = None
        self.end_pos = None
        self.area_label.config(text="No area selected")

root = tk.Tk()
app = CoordinateTracker(root)
root.mainloop()