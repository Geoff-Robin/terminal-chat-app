import socket as sck
import threading
from pymongo import MongoClient
from datetime import datetime

# MongoDB setup
db_address = ""  # MongoDB connection string should be specified here
database_client = MongoClient(db_address)
db = database_client["ChatApp"]
login_credentials = db["LoginCredentials"]

HOST = "127.0.0.1"  # Server IP address
PORT = 55555  # Port to listen on
FORMAT = 'ascii'  # Encoding format for messages
server = sck.socket(sck.AF_INET, sck.SOCK_STREAM)
server.bind((HOST, PORT))  # Bind the server to the specified IP and port

def init_chat(conn, username, channel_name):
    """
    Initialize the chat for a given user and channel.
    Sends the chat history to the user and starts receiving messages.
    """
    chat_history = db[channel_name]  # Access the chat history collection for the channel
    messages = chat_history.find().sort("time", 1)  # Retrieve and sort messages by time
    if chat_history.count_documents({}) == 0:
        conn.send("No chat history found.\n".encode(FORMAT))
    else:
        for message in messages:
            conn.send(f"{message['time']} - {message['username']}: {message['message']}\n".encode(FORMAT))
    recv_chat(conn, username, channel_name)

def recv_chat(conn, username, channel_name):
    """
    Continuously receive messages from the client and broadcast them.
    Handles the special case of the "!exit" command.
    """
    chat_history = db[channel_name]  # Access the chat history collection for the channel
    while True:
        try:
            message = conn.recv(1024).decode(FORMAT).strip()  # Receive and decode message
            if message:
                if message == "!exit":
                    # Handle user exit
                    exit_message = f"{username} has left the chat."
                    chat_history.insert_one({
                        "username": "System",
                        "message": exit_message,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    broadcast(exit_message, conn, "System", channel_name)  # Notify other users
                    remove_client(conn, channel_name)  # Remove the client
                    break
                else:
                    # Handle regular messages
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    chat_history.insert_one({
                        "username": username,
                        "message": message,
                        "time": timestamp
                    })
                    broadcast(message, conn, username, channel_name)  # Broadcast the message
            else:
                remove_client(conn, channel_name)
                break
        except Exception as e:
            print(f"Error in recv_chat: {e}")
            remove_client(conn, channel_name)
            break

def broadcast(message, conn, username, channel_name):
    """
    Broadcast a message to all clients in the specified channel, except the sender.
    """
    for client in rooms.get(channel_name, []):
        if client != conn:
            try:
                client.send(f"{username}: {message}\n".encode(FORMAT))  # Send the message to other clients
            except:
                remove_client(client, channel_name)

def remove_client(conn, channel_name):
    """
    Remove a client from the specified channel and close the connection.
    """
    if conn in rooms.get(channel_name, []):
        rooms[channel_name].remove(conn)  # Remove the client from the room
        conn.close()  # Close the client connection

def join_or_create_room(conn, username):
    """
    Prompt the user to either create a new chat room or join an existing one.
    """
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
                rooms[channel_name] = []  # Initialize the room with an empty list
                rooms[channel_name].append(conn)  # Add the client to the room
                init_chat(conn, username, channel_name)
                done = True

        elif choice == "2":
            conn.send("Enter room name to join: ".encode(FORMAT))
            channel_name = conn.recv(1024).decode(FORMAT).strip()

            # Check if the room exists in the database
            if channel_name in db.list_collection_names():
                rooms.setdefault(channel_name, []).append(conn)  # Add the client to the existing room
                init_chat(conn, username, channel_name)
                done = True
            else:
                conn.send("Chat room does not exist.\n".encode(FORMAT))

        else:
            conn.send("Invalid choice. Please enter 1 to create a room or 2 to join a room.\n".encode(FORMAT))

def login(conn):
    """
    Handle user login. If credentials are invalid, offer to sign up.
    """
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
    """
    Handle user sign-up by storing new credentials in the database.
    """
    conn.send("Enter Username: ".encode(FORMAT))
    username = conn.recv(1024).decode(FORMAT)
    conn.send("Enter Password: ".encode(FORMAT))
    password = conn.recv(1024).decode(FORMAT)
    user = {
        "username": username,
        "password": password
    }
    login_credentials.insert_one(user)  # Save the new user credentials
    join_or_create_room(conn, username)  # Proceed to join or create a chat room

def start_server():
    """
    Start the server, accept incoming connections, and handle logins/sign-ups.
    """
    server.listen()
    print("Server started and listening on port 55555")
    while True:
        conn, addr = server.accept()  # Accept a new connection
        print(f"Connection from {addr}")
        
        # Ask the user if they want to log in or sign up
        conn.send("Do you want to log in or sign up?\nPress 1 to Log In or 2 to Sign Up: ".encode(FORMAT))
        choice = conn.recv(1024).decode(FORMAT).strip()
        
        if choice == "1":
            threading.Thread(target=login, args=(conn,)).start()  # Start login thread
        elif choice == "2":
            threading.Thread(target=sign_up, args=(conn,)).start()  # Start sign-up thread
        else:
            conn.send("Invalid choice. Disconnecting...\n".encode(FORMAT))
            conn.close()  # Close connection if choice is invalid

if __name__ == "__main__":
    rooms = {}  # Dictionary to keep track of rooms and connected clients
    start_server()  # Start the server
