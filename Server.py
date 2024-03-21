import socket
import threading
from Authentication import *
import Requests
from collections import deque
import time
from fileTransfer import FileTransfer

# Constants: 
HOST = '127.0.0.1' # the most commonly used IP address on the loopback network
FORMAT = 'utf-8' # encoding format
PORT = 5000 # port to listen on - UPnP (Universal Plug and Play) 
ADDR = (HOST, PORT) # tuple of IP+PORT
RATE_LIMIT = 60 # seconds

clients = {}  # Map usernames to connection objects-> # username: {"conn": conn_object, "room": room_name}
msg_timeStamps = {} # username: deque of message timestamps

def handle_client(conn, addr):
    username = None
    try:
        print(f"[NEW CONNECTION] {addr} connected.")
        clients[addr] = {"conn": conn, "room": None}  # Initially add with addr as key
        count_active_connections()

        is_authenticated = False
        while not is_authenticated:
            conn.send("Choose an option:\n1. Sign In\n2. Register\n".encode(FORMAT))
            option = conn.recv(1024).decode(FORMAT)

            if option == "1":
                username = None
                while True:
                    credentials = conn.recv(1024).decode(FORMAT)
                    username, password = credentials.split(':')
                    is_authenticated, role = authenticate(username, password)
                    
                    if is_authenticated:
                        clients[username] = clients.pop(addr)  # Replace the connection object with the username
                        clients[username]['conn'] = conn  # Update the connection object   
                        conn.send(f"Authenticated successfully as {role}.\n".encode(FORMAT))
                        break
                    else:
                        conn.send("Authentication failed. Try again.\n".encode(FORMAT))

            elif option == "2":
                username = conn.recv(1024).decode(FORMAT)
                password = conn.recv(1024).decode(FORMAT)
                # Call register function
                if register(username, password):
                    conn.send("Registration successful. Please sign in.\n".encode(FORMAT))
                else:
                    conn.send("Registration failed. User already exists.\n".encode(FORMAT))
                continue
            
            else:
                conn.send("Invalid option. Try again.\n".encode(FORMAT))

        current_room = None # User is not in a room
        while True:
            if not current_room:
                request = conn.recv(1024).decode(FORMAT)

                if request == "create_room":
                    if role == "admin":
                        conn.send("Enter the name of the room you'd like to create: ".encode(FORMAT))
                        room_name = conn.recv(1024).decode(FORMAT).strip()
                        room_creation_success = Requests.create_room(room_name, username)
                        if room_creation_success:
                            conn.send(f"Room '{room_name}' created successfully.".encode(FORMAT))                   
                        else:
                            conn.send(f"Room '{room_name}' already exists.".encode(FORMAT))
                    else:
                        conn.send("You don't have permission to create a room.".encode(FORMAT))
                    continue

                elif request == "delete_room":
                    if role == "admin":
                        conn.send("Enter the name of the room you'd like to delete: ".encode(FORMAT))
                        room_name = conn.recv(1024).decode(FORMAT)
                        room_deletion_success = Requests.delete_room(room_name, username)
                        if room_deletion_success:
                            conn.send(f"Room '{room_name}' deleted successfully.".encode(FORMAT))
                        else:
                            conn.send(f"Room '{room_name}' does not exist or you don't have permission to delete it.".encode(FORMAT))
                    else:
                        conn.send("You don't have permission to delete a room.".encode(FORMAT))
                    continue

                elif request == "join_room":
                    conn.send("Enter the name of the room you'd like to join: ".encode(FORMAT))
                    room_name = conn.recv(1024).decode(FORMAT).strip()

                    join_response = Requests.join_room(username, room_name)
                    if join_response is not None:
                        current_room = room_name
                        previous_messages = "".join(join_response)
                        conn.send(f"Successfully joined room '{room_name}'.\n\nChat-History:\n{previous_messages}\n".encode(FORMAT))

                        while current_room:
                            msg = conn.recv(1024).decode(FORMAT).strip()
                            
                            if msg.upper() == "LEAVE":
                                Requests.leave_room(username, current_room)
                                current_room = None
                                conn.send("You have left the room.\n".encode(FORMAT))
                                break

                            current_time = time.time()
                            if username not in msg_timeStamps:
                                msg_timeStamps[username] = deque()

                            msg_timeStamps[username].append(current_time)
                            if len(msg_timeStamps[username]) > 10: # user is limited for 11 messesages in 60 seconds
                                oldest_msg_time = msg_timeStamps[username].popleft()
                                if current_time - oldest_msg_time <= RATE_LIMIT:
                                    continue  # Skip processing this message

                            # Save message to room's chat history
                            Requests.send_message_to_room(username, current_room, msg, clients)
                    else:
                        conn.send(f"Failed to join room '{room_name}'. It might not exist or you're already in the room.\n".encode(FORMAT))
                    continue

                elif request == "DISCONNECT!":
                    conn.send(f"[DISCONNECT] {username} is disconnecting...".encode(FORMAT))
                    break

                elif request == "change_password":
                    current_password = conn.recv(1024).decode(FORMAT)
                    new_password = conn.recv(1024).decode(FORMAT)
                    if change_password(username, current_password, new_password):
                        conn.send("Password changed successfully.\n".encode(FORMAT))
                    else:
                        conn.send("Failed to change password. Incorrect current password.".encode(FORMAT))

                elif request == "list_users":
                    active_users = update_active_connections()
                    users_list = "\n".join([f"{user}: {role}" for user, role in active_users.items()])
                    conn.send(f"Connected Users:\n{users_list}\n".encode(FORMAT))

                elif request.startswith("FILE_TRANSFER"):
                    _, room_name, file_name, file_size = request.split(' ', 3)
                    file_size = int(file_size)
                    file_transfer = FileTransfer(conn, room_name)
                    file_transfer.receive_file(file_name, file_size)

                    # Notify other members in the room
                    Requests.read_rooms_from_csv()  # Refresh chat_rooms
                    if room_name in Requests.chat_rooms:
                        notification = f"New file available: {file_name} from {username}"
                        for member in Requests.chat_rooms[room_name]['members']:
                            if member != username and member in clients:
                                clients[member]['conn'].send(notification.encode(FORMAT))
                        
                else:
                    conn.send(f"[ERROR] Invalid request from {addr}\n".encode(FORMAT))
                    continue
        
        print(f"[DISCONNECT] {username} is disconnecting...") # after the while loop (user disconnected)
    except(ConnectionResetError, BrokenPipeError):
        print(f"[ERROR] Unexpected disconnection from {addr}.")
    except Exception as e:
        print(f"[ERROR] Error encountered: {e}")   
    finally:     
        # cleanup
        if username:
            leave_all_rooms(username) 
            if username in clients:
                del clients[username] # Remove the user from the clients dictionary
        else:
            if addr in clients:
                del clients[addr] # Remove using addr if username was not set
        conn.close() # close the connection
        print(f"[DISCONNECT] {addr} disconnected.")
        count_active_connections()

def count_active_connections():
    print(f"[ACTIVE CONNECTIONS] {len(clients)}")

def update_active_connections():
    # Return the list of currently connected users and their roles
    active_users = {}
    for username in clients:
        user_data = read_users_from_csv()
        if username in user_data:
            active_users[username] = user_data[username]['role']
    return active_users

def leave_all_rooms(username): 
    Requests.read_rooms_from_csv()  # Refresh chat_rooms
    for room_name in Requests.chat_rooms:
        if username in Requests.chat_rooms[room_name]['members']:
            Requests.chat_rooms[room_name]['members'].remove(username)
    Requests.write_rooms_to_csv()  # Update rooms.csv with the changes

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen() # open for connection
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

    while True:
        conn , addr = server.accept()      
        thread = threading.Thread(target=handle_client, args=(conn, addr))  # new thread to handle the client
        thread.start()

if __name__ == "__main__":
    print("[STARTING] Server is starting...")
    start_server()