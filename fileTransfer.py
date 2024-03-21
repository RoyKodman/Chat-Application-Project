import os

class FileTransfer:
    def __init__(self, connection, room_name, base_folder='files'):
        self.connection = connection
        self.room_name = room_name
        self.base_folder = os.path.join(base_folder, room_name)
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)

    def send_file(self, file_path):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        self.connection.send(f"FILE_TRANSFER {self.room_name} {file_name} {file_size}".encode('utf-8'))

        with open(file_path, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                self.connection.send(data)

    def receive_file(self, file_name, file_size):
        file_path = os.path.join(self.base_folder, file_name)
        with open(file_path, 'wb') as file:
            bytes_received = 0
            while bytes_received < file_size:
                data = self.connection.recv(1024)
                file.write(data)
                bytes_received += len(data)