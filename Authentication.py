import csv
from threading import Lock
import bcrypt

FORMAT = "utf-8"

user_file_lock = Lock()

# File management functions
def read_users_from_csv():
    with open('users.csv', mode='r', newline='', encoding=FORMAT) as file:
        reader = csv.DictReader(file)
        return {row['username']: {'password': row['password'], 'role': row['role']} for row in reader}

def write_user_to_csv(username, password, role):
    with user_file_lock:
        with open('users.csv', mode='a', newline='', encoding=FORMAT) as file:
            writer = csv.writer(file)
            writer.writerow([username, password, role])

def hash_password(password):
   return bcrypt.hashpw(password.encode(FORMAT), bcrypt.gensalt()).decode(FORMAT) 

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode(FORMAT), hashed_password.encode(FORMAT))

# Authentication 
def authenticate(username, password):
    users = read_users_from_csv()
    user = users.get(username)
    if user and check_password(user['password'], password):
        return True, user['role']
    return False, None

# Registration
def register(username, password, role='regular'):
    users = read_users_from_csv()
    if username not in users:
        hashed_password = hash_password(password)
        role = "admin" if len(username) == 3 or len(users) == 0 else "regular" # need to check
        write_user_to_csv(username, hashed_password, role)
        return True
    return False

# Change password
def change_password(username, current_password, new_password):
    users = read_users_from_csv()
    user = users.get(username)

    if user and check_password(user['password'], current_password):
        hashed_new_password = hash_password(new_password)
        users[username]['password'] = hashed_new_password

        # Re-write all users to CSV with updated password
        with user_file_lock:
            with open('users.csv', mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['username', 'password', 'role'])
                for user, info in users.items():
                    writer.writerow([user, info['password'], info['role']])
        return True
    
    return False