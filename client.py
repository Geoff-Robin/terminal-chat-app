import socket
import threading
import sys

# Connecting To Server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 55555))

def receive():
    while True:
        try:
            # Receive Message From Server
            message = client.recv(1024).decode('ascii')
            if message.startswith("!exit"):
                username = message.split()
                print(f"{username[1]} has left!")
                client.close()
                sys.exit()
            else:
                print(message)
        except Exception as e:
            print(f"An error occurred: {e}")
            client.close()
            sys.exit()

def write():
    while True:
        message = input()
        if message == "!exit":
            client.send(message.encode('ascii'))
            client.close()
            sys.exit()
        client.send(message.encode('ascii'))

# Start the receiving thread
receive_thread = threading.Thread(target=receive)
receive_thread.start()

# Start the writing thread
write_thread = threading.Thread(target=write)
write_thread.start()
