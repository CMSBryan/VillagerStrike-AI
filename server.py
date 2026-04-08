import socket

# Define the host and port
HOST = '127.0.0.1'  # Localhost
PORT = 8080        # A high port that doesn't require special permissions

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"[*] Dummy server listening on {HOST}:{PORT}")
    print("[*] Press Ctrl+C to stop.")
    
    while True:
        conn, addr = s.accept()
        with conn:
            print(f"[!] Connection received from {addr}")
            conn.sendall(b"Hello from the dummy server!")