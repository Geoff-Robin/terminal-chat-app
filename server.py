import socket as sck
import threading
from pymongo import MongoClient
from datetime import datetime

# MongoDB setup
db_address=""
database_client = MongoClient(db_address)
db = database_client["ChatApp"]
login_credentials = db["LoginCredentials"]

HOST = "127.0.0.1"
PORT = 55555
FORMAT = 'ascii'
server = sck.socket(sck.AF_INET, sck.SOCK_STREAM)
server.bind((HOST, PORT))

def init_chat(conn, username, channel_name):
    chat_history = db[channel_name]
    messages = chat_history.find().sort("time", 1)
    if chat_history.count_documents({}) == 0:
        conn.send("No chat history found.\n".encode(FORMAT))
    else:
        for message in messages:
            conn.send(f"{message['time']} - {message['username']}: {message['message']}\n".encode(FORMAT))
    recv_chat(conn, username, channel_name)

def recv_chat(conn, username, channel_name):
    chat_history = db[channel_name]
    while True:
        try:
            message = conn.recv(1024).decode(FORMAT).strip()
            if message:
                if message == "!exit":
                    exit_message = f"{username} has left the chat."
                    chat_history.insert_one({
                        "username": "System",
                        "message": exit_message,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    broadcast(exit_message, conn, "System", channel_name)
                    remove_client(conn, channel_name)
                    break
                else:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    chat_history.insert_one({
                        "username": username,
                        "message": message,
                        "time": timestamp
                    })
                    broadcast(message, conn, username, channel_name)
            else:
                remove_client(conn, channel_name)
                break
        except Exception as e:
            print(f"Error in recv_chat: {e}")
            remove_client(conn, channel_name)
            break

def broadcast(message, conn, username, channel_name):
    for client in rooms.get(channel_name, []):
        if client != conn:
            try:
                client.send(f"{username}: {message}\n".encode(FORMAT))
            except:
                remove_client(client, channel_name)

def remove_client(conn, channel_name):
    if conn in rooms.get(channel_name, []):
        rooms[channel_name].remove(conn)
        conn.close()

def join_or_create_room(conn, username):
    done = False
    while not done:
        conn.send("Do you want to create a room or join an existing room?\nPress 1 to Create Room or 2 to Join Room: ".encode(FORMAT))
        choice = conn.recv(1024).decode(FORMAT).strip()

        if choice == "1":
            conn.send("Enter room name to create: ".encode(FORMAT))
            channel_name = conn.recv(1024).decode(FORMAT).strip()

            # Check if the room already exists in the database
            if channel_name in db.list_collection_names():
                conn.send("Room already exists. Please choose a different name.\n".encode(FORMAT))
            else:
                # Create the room and add the client
                db.create_collection(channel_name)  # Create a new collection for the room
                rooms[channel_name] = []
                rooms[channel_name].append(conn)
                init_chat(conn, username, channel_name)
                done = True

        elif choice == "2":
            conn.send("Enter room name to join: ".encode(FORMAT))
            channel_name = conn.recv(1024).decode(FORMAT).strip()

            # Check if the room exists in the database
            if channel_name in db.list_collection_names():
                rooms.setdefault(channel_name, []).append(conn)
                init_chat(conn, username, channel_name)
                done = True
            else:
                conn.send("Chat room does not exist.\n".encode(FORMAT))

        else:
            conn.send("Invalid choice. Please enter 1 to create a room or 2 to join a room.\n".encode(FORMAT))

def login(conn):
    login = False
    count = 1
    while not login:
        conn.send("Enter Username: ".encode(FORMAT))
        username = conn.recv(1024).decode(FORMAT)
        conn.send("Enter Password: ".encode(FORMAT))
        password = conn.recv(1024).decode(FORMAT)
        count += 1
        if login_credentials.find_one({'username': username, 'password': password}) is not None:
            login = True
            join_or_create_room(conn, username)
        else:
            conn.send("Invalid credentials. Try again.\n".encode(FORMAT))
            if count > 1:
                conn.send("If you don't have an account, please try signing up!\nTo sign press 1".encode(FORMAT))
                c1 = conn.recv(1024).decode(FORMAT)
                if c1 == "1":
                    sign_up(conn)

def sign_up(conn):
    conn.send("Enter Username: ".encode(FORMAT))
    username = conn.recv(1024).decode(FORMAT)
    conn.send("Enter Password: ".encode(FORMAT))
    password = conn.recv(1024).decode(FORMAT)
    user = {
        "username": username,
        "password": password
    }
    login_credentials.insert_one(user)
    join_or_create_room(conn, username)

def start_server():
    server.listen()
    print("Server started and listening on port 55555")
    while True:
        conn, addr = server.accept()
        print(f"Connection from {addr}")
        
        # Ask the user if they want to log in or sign up
        conn.send("Do you want to log in or sign up?\nPress 1 to Log In or 2 to Sign Up: ".encode(FORMAT))
        choice = conn.recv(1024).decode(FORMAT).strip()
        
        if choice == "1":
            threading.Thread(target=login, args=(conn,)).start()
        elif choice == "2":
            threading.Thread(target=sign_up, args=(conn,)).start()
        else:
            conn.send("Invalid choice. Disconnecting...\n".encode(FORMAT))
            conn.close()

if __name__ == "__main__":
    rooms = {}
    start_server()
