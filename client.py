import socket
import threading
import sys

# Create a socket object for connecting to the server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server at the specified IP address and port
client.connect(('127.0.0.1', 55555))

def receive():
    """Function to handle receiving messages from the server."""
    while True:
        try:
            # Receive message from server
            message = client.recv(1024).decode('ascii')
            
            # Check if the message is an exit command
            if message.startswith("!exit"):
                username = message.split()  # Split the message to get the username
                print(f"{username[1]} has left!")  # Inform other clients that this user has left
                client.close()  # Close the connection to the server
                sys.exit()  # Exit the program

            else:
                # Print the received message
                print(message)
        
        except Exception as e:
            # Print error message if an exception occurs
            print(f"An error occurred: {e}")
            client.close()  # Close the connection to the server
            sys.exit()  # Exit the program

def write():
    """Function to handle sending messages to the server."""
    while True:
        message = input()  # Get input from the user
        if message == "!exit":
            client.send(message.encode('ascii'))  # Send the exit command to the server
            client.close()  # Close the connection to the server
            sys.exit()  # Exit the program
        client.send(message.encode('ascii'))  # Send the user input to the server

# Start a new thread for receiving messages from the server
receive_thread = threading.Thread(target=receive)
receive_thread.start()

# Start a new thread for sending messages to the server
write_thread = threading.Thread(target=write)
write_thread.start()
