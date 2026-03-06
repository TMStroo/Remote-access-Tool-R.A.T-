import socket
import threading
import time
import io
import json
import os
import sys
import mss
import pyautogui
from PIL import Image

# Configuration
DEFAULT_PORT = 5566 # Changed from 5555 to avoid common blocks
QUALITY = 50 
SCREENSHOT_DELAY = 0.05

def get_local_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        _, _, addresses = socket.gethostbyname_ex(hostname)
        ips = [ip for ip in addresses if not ip.startswith("127.")]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary = s.getsockname()[0]
            s.close()
            if primary not in ips:
                ips.insert(0, primary)
        except: pass
    except: pass
    return ips if ips else ["Unknown"]

def send_screen(conn):
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            try:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=QUALITY)
                data = buffer.getvalue()
                conn.sendall(len(data).to_bytes(4, byteorder='big'))
                conn.sendall(data)
                time.sleep(SCREENSHOT_DELAY)
            except: break

def handle_commands(conn):
    while True:
        try:
            data_len_bytes = conn.recv(4)
            if not data_len_bytes: break
            data_len = int.from_bytes(data_len_bytes, byteorder='big')
            data = conn.recv(data_len).decode('utf-8')
            cmd = json.loads(data)
            action = cmd.get('type')
            params = cmd.get('params')
            if action == 'mouse_move':
                pyautogui.moveTo(params['x'], params['y'], _pause=False)
            elif action == 'mouse_click':
                pyautogui.click(button=params['button'], _pause=False)
            elif action == 'key_press':
                pyautogui.press(params['key'], _pause=False)
        except: break

def background_server(local_ips):
    """Runs the socket server in a secondary thread"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('0.0.0.0', DEFAULT_PORT))
        server_socket.listen(5)
        print(f"Server Background Thread started on Port {DEFAULT_PORT}")
    except Exception as e:
        print(f"Background Server Error: {e}")
        return

    while True:
        try:
            conn, addr = server_socket.accept()
            print(f"Connected by {addr}")
            screen_size = pyautogui.size()
            res_data = json.dumps({'width': screen_size.width, 'height': screen_size.height}).encode('utf-8')
            conn.sendall(len(res_data).to_bytes(4, byteorder='big'))
            conn.sendall(res_data)
            
            t1 = threading.Thread(target=send_screen, args=(conn,))
            t2 = threading.Thread(target=handle_commands, args=(conn,))
            t1.daemon = True
            t2.daemon = True
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            conn.close()
        except: time.sleep(1)

def discovery_broadcaster():
    """Broadcasts service presence via UDP so controllers can find it."""
    broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    hostname = socket.gethostname()
    msg = json.dumps({'service': 'controlled_remote', 'hostname': hostname}).encode('utf-8')
    
    while True:
        try:
            broadcast_socket.sendto(msg, ('<broadcast>', 5567))
            time.sleep(2)
        except:
            time.sleep(5)

def main():
    pyautogui.FAILSAFE = False
    local_ips = get_local_ips()
    
    # Start Discovery Broadcaster
    d_thread = threading.Thread(target=discovery_broadcaster)
    d_thread.daemon = True
    d_thread.start()

    # Start server in BACKGROUND thread
    server_thread = threading.Thread(target=background_server, args=(local_ips,))
    server_thread.daemon = True
    server_thread.start()
    
    print("Controlled service is running in the background...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
