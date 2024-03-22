# Group-Chat Application with Client-Server Architecture

## Introduction
A Python group chat application implemented with a Client-Server architecture, supporting [features](#features) like user authentication, dynamic room creation and management, and file transfers.

Developed as a final project in "Computer Networks and Internet" course, Bar-Ilan University,
This project demonstrates practical applications of network protocols and socket programming.

## Technologies
- Python
- Socket Programming
- Multithreading
- CSV File Handling
- bcrypt for Password Hashing

## Installation
Clone the repository and install `Python 3.x`. 

For password hashing, install bcrypt using `pip install bcrypt`.

## Usage
Run `Server.py` to start the server. Then run `Client.py` and use it to connect to the server. 

The Client offers options for user authentication, room management, and file transfer.

## Features
- User Authentication (Login/Register)
- Dynamic Room Creation and Deletion (Admin roles)
- Real-time Message Exchange in Rooms
- Rate Limiting for Message Sending (To prevent abuse)
- File Transfer within Rooms

## License
This project is licensed under the [MIT License](LICENSE).

## Contribution
Contributions are welcome. Please fork the repository and submit a pull request with your changes.

## Contact
Reach out via roykod18@gmail.com or www.linkedin.com/in/roykodman for any queries.
