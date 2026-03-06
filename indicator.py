import tkinter as tk
import os
import signal

def start_indicator():
    root = tk.Tk()
    root.title("Control Indicator")
    
    # Stay on top
    root.attributes("-topmost", True)
    # Remove window decorations (optional, but makes it look more like an overlay)
    # root.overrideredirect(True) 
    
    # Set size and position (top right corner)
    width = 250
    height = 80
    screen_width = root.winfo_screenwidth()
    x = screen_width - width - 20
    y = 50
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    root.configure(bg="#ff4d4d") # Red background for visibility
    
    label = tk.Label(root, text="REMOTE CONTROL ACTIVE", fg="white", bg="#ff4d4d", font=("Arial", 12, "bold"))
    label.pack(pady=5)
    
    def on_stop():
        print("Stopping remote control session...")
        # In a real scenario, this might need to signal the parent process
        # For now, we'll exit the process
        os._exit(0)

    stop_button = tk.Button(root, text="DISCONNECT", command=on_stop, bg="white", fg="#ff4d4d", font=("Arial", 10, "bold"))
    stop_button.pack(pady=5)
    
    # Allow moving the window if needed (since we might use overrideredirect)
    def start_move(event):
        root.x = event.x
        root.y = event.y

    def stop_move(event):
        root.x = None
        root.y = None

    def on_motion(event):
        deltax = event.x - root.x
        deltay = event.y - root.y
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")

    root.bind("<Button-1>", start_move)
    root.bind("<ButtonRelease-1>", stop_move)
    root.bind("<B1-Motion>", on_motion)

    root.mainloop()

if __name__ == "__main__":
    start_indicator()
