import socket
import time
from collections import deque
import threading
from fileTransfer import FileTransfer

HOST = '127.0.0.1' 
FORMAT = 'utf-8' 
PORT = 5000 
ADDR = (HOST, PORT)
RATE_LIMIT = 60  # seconds
msg_timeStamps = deque()

listening = True
left_room = False  # Flag to indicate if the user has left the room

def listen_for_messages(client_socket):
    global listening, left_room
    while listening:
        try:
            message = client_socket.recv(1024).decode(FORMAT)
            if message:
                # Stop printing prompts if the user has left the room
                if message == "You have left the room.\n":
                    left_room = True
                    print(message.strip())
                    break
                print(f"\n{message}\n>>> ", end="", flush=True)
        except Exception as e:
            if not listening or left_room:
                break
            print(f"Error receiving message: {e}")

def handle_room_chat(client_socket):
    global listening, left_room
    listening = True
    left_room = False
    listener_thread = threading.Thread(target=listen_for_messages, args=(client_socket,))
    listener_thread.start()

    while listening and not left_room:
        message = input(">>> ")
        if message.upper() == "LEAVE":
            client_socket.send(message.encode(FORMAT))
            left_room = True  # Set flag to indicate user has left the room
            break

        elif message.startswith("!sendfile"):
            try:
                _, room_name, file_path = message.split(maxsplit=2)
                file_transfer = FileTransfer(client_socket, room_name)
                file_transfer.send_file(file_path)
                print("File sent successfully.")
            except ValueError:
                print("Usage: !sendfile <room_name> <file_path>")
            except FileNotFoundError:
                print("File not found.")
            except Exception as e:
                print(f"Error sending file: {e}")
        
        else:
            client_socket.send(message.encode(FORMAT))

        # Check if rate limit is exceeded
        current_time = time.time()
        if len(msg_timeStamps) >= 10: # user is limited for 11 messesages in 60 seconds
            oldest_msg_time = msg_timeStamps[0]
            if current_time - oldest_msg_time < RATE_LIMIT:
                print("Rate limit exceeded. Please wait before sending more messages.")
                time.sleep(RATE_LIMIT - (current_time - oldest_msg_time))  # Pause for the remainder of the rate limit period
                continue
        
        # Update timestamps queue
        msg_timeStamps.append(current_time)
        if len(msg_timeStamps) > 10: 
            msg_timeStamps.popleft()

    listener_thread.join() # Ensure the listener thread has finished
    print_main_menu()

def print_main_menu():
    print("\nWelcome to the group chat!\n" +
          "Enter a request:\n" +
          "*create_room\n" +
          "*join_room\n" +
          "*delete_room\n" +
          "*change_password\n" +
          "*list_users\n" +
          "*DISCONNECT!\n")

def start_client():
    try:
        # Connect to the server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(ADDR)

        authorized = False
        while not authorized:
            server_msg = client.recv(1024).decode(FORMAT)
            print(f"[SERVER] {server_msg}")
            choice = input("your choice (1/2): ")
            client.send(choice.encode(FORMAT))

            if choice == "1":
                while not authorized: # Authentication
                    username = input("Enter username: ")
                    password = input("Enter password: ")
                    client.send(f"{username}:{password}".encode(FORMAT))
                    auth_response = client.recv(1024).decode(FORMAT)
                    print(f"[SERVER] {auth_response}")
                    authorized = "Authenticated successfully" in auth_response
                    
            elif choice == "2":
                print("Register new user.\n")
                username = input("Enter username: ")
                client.send(username.encode(FORMAT))
                password = input("Enter password: ")
                client.send(password.encode(FORMAT))
                print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")
                continue
            else:
                print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")  # need to check
                continue
        
        print_main_menu()  # Print the main menu initially after authentication

        if authorized:
            while True:
                request = input("Your request: ")
                client.send(request.encode(FORMAT))

                if request == "create_room":
                    room_creation_response = client.recv(1024).decode(FORMAT)
                    print(room_creation_response)
                    if "Enter the name" in room_creation_response:
                        room_name = input()
                        client.send(room_name.encode(FORMAT))
                        creation_status = client.recv(1024).decode(FORMAT)
                        print(f"[SERVER] {creation_status}")

                elif request == "delete_room":
                    room_deletion_response = client.recv(1024).decode(FORMAT)
                    print(room_deletion_response)
                    if "Enter the name" in room_deletion_response:
                        room_name = input()
                        client.send(room_name.encode(FORMAT))
                        deletion_status = client.recv(1024).decode(FORMAT)
                        print(f"[SERVER] {deletion_status}")

                elif request == "join_room":
                    print(client.recv(1024).decode(FORMAT)) # Prompt for room name
                    room_name = input()
                    client.send(room_name.encode(FORMAT))
                    join_room_response = client.recv(1024).decode(FORMAT)
                    print(join_room_response)

                    if "Successfully joined" in join_room_response:
                        handle_room_chat(client)
                        continue

                elif request == "DISCONNECT!":
                    print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")
                    break

                elif request == "change_password":
                    current_password = input("Enter your current password: ")
                    client.send(current_password.encode(FORMAT))
                    new_password = input("Enter your new password: ")
                    client.send(new_password.encode(FORMAT))
                    print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")

                elif request == "list_users":
                    print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")
            
                else:
                    print(f"[SERVER] {client.recv(1024).decode(FORMAT)}")

                print_main_menu()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()  # Ensure the connection is closed in case of error
        print("\n[CLOSING CONNECTION] client closed socket!")


if __name__ == "__main__":
    print("[CLIENT] Started running")
    start_client()
    print("\nGoodbye client:)")