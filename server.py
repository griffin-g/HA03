import socket
import threading
import os
import time

IP_Addr = 'localhost'
port = 8080
BUFFER_SIZE = 4096

clients = {}
clients_lock = threading.Lock()

# broadcasts a message of type CHAT to all users except for the sender
def broadcast(message, sender_conn=None):
    prefix = 'CHAT:'
    broadcast_msg = f"{prefix}{message}".encode('utf-8')
    with clients_lock:
        for conn in clients:
            if conn != sender_conn:
                try:
                    conn.sendall(broadcast_msg)
                except Exception as e:
                    print(f"Error sending message to {clients[conn]}: {e}")
                    remove_client(conn)

# remove client from the server and notify all other users
def remove_client(conn):
    with clients_lock:
        if conn in clients:
            name = clients[conn]
            del clients[conn]
            exit_msg = f"SERVER: {name} has left the chat.\n"
            print(f"{name} has disconnected.")
            broadcast(exit_msg, conn)
    conn.close()

# handles connected client from addr
def handle_client(conn, addr):
    print(f"Client connected from {addr}")
    try:
        while True:
            # Receive the message type header from client
            header = conn.recv(5)  # header as 'CHAT:' or 'FILE:'
            if not header:
                break

            header = header.decode('utf-8')

            # Client sent chat message
            if header == 'CHAT:':
                message = conn.recv(1024).decode('utf-8').strip()
                if message:
                    client_chat_msg = f"{clients[conn]}: {message}"
                    print(f"{clients[conn]}: {message}")
                    broadcast(client_chat_msg, conn)
            elif header == 'FILE:':
                # Handle file transfer
                # Receive filename
                filename = conn.recv(1024).decode('utf-8').strip()
                if not filename:
                    print(f"Client {clients[conn]} sent an empty filename.")
                    continue

                # Receive filesize
                filesize_data = conn.recv(16).decode('utf-8').strip()
                if not filesize_data.isdigit():
                    print(f"Client {clients[conn]} sent invalid filesize.")
                    continue
                filesize = int(filesize_data)
                # Prepare to receive the file
                unique_filename = f"{os.path.splitext(filename)[0]}_{time.time()}{os.path.splitext(filename)[1]}"
                with open(unique_filename, 'wb') as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        bytes_read = conn.recv(min(BUFFER_SIZE, filesize - bytes_received))
                        if not bytes_read:
                            break
                        f.write(bytes_read)
                        bytes_received += len(bytes_read)

                print(f"Received file '{unique_filename}' from {clients[conn]}")
                # Notify all clients about the new file
                notification = f"SERVER: {clients[conn]} has sent a file '{unique_filename}'.".encode('utf-8')
                broadcast(notification, conn)
            else:
                print(f"Unknown header received from {clients[conn]}: {header}")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        remove_client(conn)

def accept_connections(server_socket):
    client_id = 0
    while True:
        try:
            conn, addr = server_socket.accept()
            client_id += 1
            conn.sendall("Please enter your name: ".encode('utf-8'))
            # client inputs name
            name = conn.recv(1024).decode('utf-8').strip()
            with clients_lock:
                clients[conn] = name
            welcome_message = f"SERVER: {name} has joined the chat."
            print(f"{name} has connected.")
            broadcast(welcome_message, conn)
            # Start a new thread for the client
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()
        except Exception as e:
            print(f"Error accepting connections: {e}")
            break

# handle the server operations and chat functions
def handle_server():
    print("\n--- Server Operator Interface ---")
    print("Commands:")
    print("/broadcast <message>          - Send a chat message to all clients")
    print("/sendfile <filepath>     - Send a file to all clients")
    print("/exit                       - Shut down the server\n")

    while True:
        try:
            command = input("").strip()
            if not command:
                continue

            if command.startswith("/broadcast "):
                message = command[len("/broadcast "):].strip()
                if message:
                    full_message = f"SERVER: {message}"
                    broadcast(full_message)
                else:
                    print("Usage: /sendall <message>")
            elif command.startswith("/sendfile "):
                filepath = command[len("/sendfile "):].strip()
                if os.path.isfile(filepath):
                    send_file(filepath)
                else:
                    print(f"File '{filepath}' does not exist.")
            elif command == "/exit":
                print("Shutting down the server...")
                os._exit(0)
            else:
                print("Unknown command.")
        except Exception as e:
            print(f"Error in operator interface: {e}")

# send file to connected clients
def send_file(filepath):
    if not os.path.isfile(filepath):
        print("File does not exist.")
        return
    
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    with clients_lock:
        for conn in clients:
            try:
                # Send file header
                conn.sendall("FILE:".encode('utf-8'))
                conn.sendall(filename.encode('utf-8'))
                conn.sendall(f"{filesize}".encode('utf-8'))

                # Send the file data
                with open(filepath, 'rb') as f:
                    while True:
                        bytes_read = f.read(BUFFER_SIZE)
                        if not bytes_read:
                            break
                        conn.sendall(bytes_read)
                print(f"Sent file '{filename}' to {clients[conn]}")
            except Exception as e:
                print(f"Error sending file to {clients[conn]}: {e}")
                remove_client(conn)

# handles server initialization and closure
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((IP_Addr, port))
        server_socket.listen()
        print(f"Server started on {IP_Addr}:{port}. Waiting for connections...")

        # Start the server user thread
        operator_thread = threading.Thread(target=handle_server, daemon=True)
        operator_thread.start()

        accept_connections(server_socket)
    

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()
        print("Server shutdown.")

if __name__ == "__main__":
    start_server()