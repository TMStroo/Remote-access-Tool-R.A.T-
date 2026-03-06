import socket
import cv2
import numpy as np
import json
import io
import os
from PIL import Image

# Configuration
PORT = 5566

def receive_all(sock, n):
    data = b''
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        except Exception:
            return None
    return data

def find_controlled_server():
    """Listens for UDP broadcasts from the 'controlled' side."""
    print("Searching for controlled machines on local network...")
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discovery_socket.bind(('', 5567)) # Listener port
    discovery_socket.settimeout(5.0)

    try:
        data, addr = discovery_socket.recvfrom(1024)
        info = json.loads(data.decode('utf-8'))
        if info.get('service') == 'controlled_remote':
            print(f"Found machine: {info.get('hostname')} at {addr[0]}")
            return addr[0]
    except socket.timeout:
        print("No machine found automatically.")
    finally:
        discovery_socket.close()
    return None

def start_controller():
    print("--- Remote Controller Menu ---")
    print("1. Scan for machines on local network")
    print("2. Enter IP address manually (Remote/Local)")
    choice = input("Select an option (1-2): ").strip()

    target_ip = None
    ip_cache_file = "last_ip.txt"

    if choice == '1':
        target_ip = find_controlled_server()
        if not target_ip:
            print("Scan failed to find any machines.")
            # Fallback to menu or manual if needed? User wants 2 options.
            # We'll allow falling back to manual if scan fails.
            print("Falling back to manual entry...")
    
    if not target_ip: # Either chose 2, or scan failed
        last_ip = ""
        if os.path.exists(ip_cache_file):
            try:
                with open(ip_cache_file, "r") as f:
                    last_ip = f.read().strip()
            except: pass

        default_ip = last_ip if last_ip else "127.0.0.1"
        prompt = f"Enter the IP address (Last/Default: {default_ip}): "
        target_ip = input(prompt).strip()
        if not target_ip:
            target_ip = default_ip

    # Save the IP for next time
    try:
        with open(ip_cache_file, "w") as f:
            f.write(target_ip)
    except: pass

    print(f"Connecting to {target_ip}:{PORT}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((target_ip, PORT))
        print("Connected!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 1. Receive screen resolution
    len_bytes = receive_all(sock, 4)
    if not len_bytes: return
    res_len = int.from_bytes(len_bytes, byteorder='big')
    res_data = receive_all(sock, res_len).decode('utf-8')
    remote_res = json.loads(res_data)
    remote_w, remote_h = remote_res['width'], remote_res['height']
    print(f"Remote Screen Resolution: {remote_w}x{remote_h}")
    
    window_name = f"Remote Control - {target_ip}"
    # WINDOW_AUTOSIZE prevents manual resizing and fits the window to the image
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.resizeWindow(window_name, remote_w, remote_h)
    
    def mouse_callback(event, x, y, flags, param):
        _, _, win_w, win_h = cv2.getWindowImageRect(window_name)
        # Avoid division by zero
        if win_w == 0 or win_h == 0: return
        rx = int(x * remote_w / win_w)
        ry = int(y * remote_h / win_h)
        
        cmd = None
        if event == cv2.EVENT_MOUSEMOVE:
            cmd = {'type': 'mouse_move', 'params': {'x': rx, 'y': ry}}
        elif event == cv2.EVENT_LBUTTONDOWN:
            cmd = {'type': 'mouse_click', 'params': {'button': 'left', 'x': rx, 'y': ry}}
        elif event == cv2.EVENT_RBUTTONDOWN:
            cmd = {'type': 'mouse_click', 'params': {'button': 'right', 'x': rx, 'y': ry}}
        
        if cmd:
            try:
                cmd_bytes = json.dumps(cmd).encode('utf-8')
                sock.sendall(len(cmd_bytes).to_bytes(4, byteorder='big'))
                sock.sendall(cmd_bytes)
            except:
                pass

    cv2.setMouseCallback(window_name, mouse_callback)

    try:
        while True:
            # Receive Screen Frame
            size_bytes = receive_all(sock, 4)
            if size_bytes is None: break
            
            size = int.from_bytes(size_bytes, byteorder='big')
            img_data = receive_all(sock, size)
            if img_data is None: break
            
            # Decode JPEG
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is not None:
                cv2.imshow(window_name, img)
            
            # Keyboard Capture
            key = cv2.waitKey(1) & 0xFF
            if key == 27: # ESC to quit
                break
            elif key != 255:
                # Map special keys to PyAutoGUI names
                if key == 13: # Enter
                    key_val = 'enter'
                elif key == 8: # Backspace
                    key_val = 'backspace'
                elif key == 9: # Tab
                    key_val = 'tab'
                else:
                    key_val = chr(key)
                
                cmd = {'type': 'key_press', 'params': {'key': key_val}}
                cmd_bytes = json.dumps(cmd).encode('utf-8')
                sock.sendall(len(cmd_bytes).to_bytes(4, byteorder='big'))
                sock.sendall(cmd_bytes)

    except Exception as e:
        print(f"Controller error: {e}")
    finally:
        print("Closing connection...")
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    start_controller()
