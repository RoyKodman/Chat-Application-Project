import csv
import os
from threading import Lock

FORMAT = "utf-8"

file_lock = Lock()

chat_rooms = {} # {room_name: {'members': [username1, username2, ...], 'admin': admin_username}}

def read_rooms_from_csv():
    with open('rooms.csv', mode='r', newline='', encoding=FORMAT) as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header row
        for row in reader:
            room_name, members, admin = row[0], row[1].split(','), row[2]
            chat_rooms[room_name] = {'members': members, 'admin': admin}

read_rooms_from_csv()

def write_rooms_to_csv():
    with file_lock:
        with open('rooms.csv', mode='w', newline='', encoding=FORMAT) as file:
            writer = csv.writer(file)
            writer.writerow(['Room Name', 'Members', 'Admin'])
            for room_name, room_info in chat_rooms.items():
                writer.writerow([room_name, ','.join(room_info['members']), room_info['admin']])

def get_room_messages_file(room_name):
    return f"{room_name}_messages.txt"

def read_room_messages(room_name):
    messages_file = get_room_messages_file(room_name)
    if os.path.exists(messages_file):
        with open(messages_file, "r", encoding=FORMAT) as file:
            return file.readlines()
    return []


def create_room(room_name, admin_user):
    read_rooms_from_csv()  # Refresh chat_rooms
    if room_name not in chat_rooms:
        chat_rooms[room_name] = {'members': [], 'admin': admin_user}
        write_rooms_to_csv()  # Save changes
        return True
    return False # room already exists

def delete_room(room_name, requesting_user):
    read_rooms_from_csv()  # Refresh chat_rooms
    if room_name in chat_rooms and (chat_rooms[room_name]['admin'] == requesting_user or requesting_user == 'admin'):
        del chat_rooms[room_name]
        write_rooms_to_csv()  # Save changes
        return True
    return False  # Room does not exist or user lacks permission

def join_room(username, room_name):
    read_rooms_from_csv()  # Refresh chat_rooms
    if room_name in chat_rooms and username not in chat_rooms[room_name]['members']:
        chat_rooms[room_name]['members'].append(username)
        write_rooms_to_csv()  # Save changes        
        return read_room_messages(room_name) # Return the messages of the room
    return None  # Room does not exist or user is already a member

def leave_room(username, room_name):
    read_rooms_from_csv()  # Refresh chat_rooms
    if room_name in chat_rooms and username in chat_rooms[room_name]['members']:
        chat_rooms[room_name]['members'].remove(username)
        write_rooms_to_csv()  # Save changes
        return True
    return False

def send_message_to_room(sender, room_name, message, clients):
    if room_name in chat_rooms:
        messages_file = get_room_messages_file(room_name)
        with file_lock, open(messages_file, "a", encoding=FORMAT) as file:
            file.write(f"{sender}: {message}\n")

        # Broadcast the message to all members in the room
        for member in chat_rooms[room_name]['members']:
            if member in clients and member != sender:
                client_conn = clients[member]['conn']
                try:
                    client_conn.send(f"{sender}: {message}".encode(FORMAT))
                except Exception as e:
                    print(f"Error sending message to {member}: {e}")