import socket
import threading
import sys
import os
import time

# Server configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 8080
BUFFER_SIZE = 4096  # Increased buffer size for file transfers

# receive messages from server
def receive_messages(server):
    while True:
        try:
            # First, receive the message type header
            header = server.recv(5)  # 'CHAT:' or 'FILE:'
            if not header:
                print("\nDisconnected from server.")
                break

            header = header.decode('utf-8')

            if header == 'CHAT:':
                # Receive and print the chat message
                message = server.recv(BUFFER_SIZE).decode('utf-8').strip()
                if message:
                    print(f"\n{message}")
                    print("<You> ", end='', flush=True)
            elif header == 'FILE:':
                filename = server.recv(1024).decode('utf-8').strip()
                if not filename:
                    print("Server sent an empty filename.")
                    continue
                
                # Receive filesize
                filesize_data = server.recv(16).decode('utf-8').strip()
                if not filesize_data.isdigit():
                    print("Server sent invalid filesize.")
                    continue
                filesize = int(filesize_data)
                # Prepare to receive the file
                unique_filename = f"{os.path.splitext(filename)[0]}_{time.time()}{os.path.splitext(filename)[1]}"
                with open(unique_filename, 'wb') as f:
                    bytes_received = 0
                    while bytes_received < filesize:
                        bytes_read = server.recv(min(BUFFER_SIZE, filesize - bytes_received))
                        if not bytes_read:
                            break
                        f.write(bytes_read)
                        bytes_received += len(bytes_read)
            else:
                print("\nUnknown message type received.")
                print("<You> ", end='', flush=True)
        except Exception as e:
            print(f"\nError receiving message: {e}")
            break

# send chat message with the header "CHAT:"
def send_chat(sock, message):
    try:
        sock.sendall("CHAT:".encode('utf-8') + message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message: {e}")

# Send file with file header
def send_file(sock, filepath):
    # Check for file 
    if not os.path.isfile(filepath):
        print("File does not exist.")
        return

    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    try:
        # Send file header
        sock.sendall("FILE:".encode('utf-8'))
        sock.sendall(filename.encode('utf-8'))
        sock.sendall(f"{filesize}".encode('utf-8'))

        # Send the file data
        with open(filepath, 'rb') as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                sock.sendall(bytes_read)
        print(f"File '{filename}' sent successfully.")
    except Exception as e:
        print(f"Error sending file: {e}")

# main client function
if __name__ == "__main__":
    # init client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except Exception as e:
        print(f"Unable to connect to server: {e}")
        sys.exit()

    # Receive server's prompt for name
    # User inputs name, else "Guest"
    try:
        prompt = client_socket.recv(1024).decode('utf-8')
        name = input(prompt)
        if not name:
            name = "Guest"
        client_socket.sendall(name.encode('utf-8'))
    except Exception as e:
        print(f"Error during initial communication: {e}")
        client_socket.close()
        sys.exit()

    print(f"Connected to chat server at {SERVER_HOST}:{SERVER_PORT}. You can start sending messages.")
    print("Type '/file <filepath>' to send a file or '/exit' to exit.")

    # Start a thread to listen for incoming messages
    recv_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
    recv_thread.start()

    while True:
        try:
            message = input("<You> ").strip()
            if not message:
                continue
            if message.lower().startswith("/file"):
                parts = message.split(' ', 1)
                file_path = parts[1].strip()
                send_file(client_socket, file_path)
            elif message.lower() == "/exit":
                print("Exiting chat...")
                client_socket.close()
                sys.exit()
            else:
                send_chat(client_socket, message)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat...")
            client_socket.close()
            sys.exit()
        except Exception as e:
            print(f"An error occurred: {e}")
            client_socket.close()
            sys.exit()

