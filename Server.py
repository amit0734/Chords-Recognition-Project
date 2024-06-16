import socket
import threading
import struct
import sqlite3
import Identify_Chords
import json
import hashlib
from rsa import RSAEncryption
from aes import AESEncryption


class Server:
    """
    This class handles server operations for a chord identification application.
    It manages client connections, user authentication, and audio processing.
    """

    def __init__(self, host='localhost', port=65433):
        """
        Initialize the server with the given host and port.

        Parameters:
        host (str): Hostname or IP address to bind the server to.
        port (int): Port number to bind the server to.
        """
        self.host = host
        self.port = port
        self.active_connections = 0
        self.lock = threading.Lock()
        self.filepath = ""
        self.bpm = 0
        self.rsa = RSAEncryption()
        self.aes_key = None
        self.model_path = 'C:\\Users\\Amit Sibony\\Downloads\\trained_model2.joblib'

    def recv_exactly(self, client_socket, n):
        """
        Receive exactly n bytes from the client socket.

        Parameters:
        client_socket (socket): The client socket.
        n (int): The number of bytes to receive.

        Returns:
        bytes: The received data.
        """
        data = b''
        while len(data) < n:
            packet = client_socket.recv(n - len(data))
            if not packet:
                raise ConnectionError("Socket connection broken")
            data += packet
        return data

    def handle_client_connection(self, client_socket, client_address):
        """
        Handle a client connection.

        Parameters:
        client_socket (socket): The client socket.
        client_address (tuple): The client address.
        """
        with self.lock:
            self.active_connections += 1
            print(f"Accepted connection from {client_address}. Total connections: {self.active_connections}")

        try:
            # Send public key to client
            public_key_pem = self.rsa.get_public_key_pem()
            client_socket.sendall(struct.pack('>I', len(public_key_pem)) + public_key_pem)

            # Receive AES key
            aes_key_length_data = self.recv_exactly(client_socket, 4)
            aes_key_length = struct.unpack('>I', aes_key_length_data)[0]
            encrypted_aes_key = self.recv_exactly(client_socket, aes_key_length)
            self.aes_key = self.rsa.decrypt(encrypted_aes_key)
            self.aes = AESEncryption(self.aes_key)

            while True:
                header = self.recv_exactly(client_socket, 8)
                if not header:
                    break

                message_type, message_length = struct.unpack('>II', header)
                encrypted_message = self.recv_exactly(client_socket, message_length)
                message = self.aes.decrypt(encrypted_message).decode()
                print(f"Received message of type {message_type} with length {message_length}: {message}")

                if message_type == 0:
                    self.handle_non_essential_message(message)
                elif message_type == 1:
                    self.handle_signup(client_socket, message)
                elif message_type == 2:
                    self.handle_signin(client_socket, message)
                elif message_type == 3:
                    self.handle_bpm_set(message)
                elif message_type == 4:
                    self.handle_open_file(message)
                elif message_type == 5:
                    self.handle_process_audio(client_socket)
                elif message_type == 6:
                    break

        finally:
            with self.lock:
                self.active_connections -= 1
                print(f"Connection from {client_address} has been closed. Total connections: {self.active_connections}")
            client_socket.close()

    def handle_non_essential_message(self, message):
        """Handle non-essential messages."""
        print(f"Non-essential action: {message}")

    def handle_signup(self, client_socket, message):
        """
        Handle user sign-up.

        Parameters:
        client_socket (socket): The client socket.
        message (str): The sign-up message.
        """
        parts = message.split(":", 4)
        if len(parts) < 5:
            response = self.aes.encrypt(b"Signup failed - Incomplete signup information")
            client_socket.sendall(struct.pack('>I', len(response)) + response)
            return
        _, username, password, email, favorite_animal = parts
        if self.insert_user(username.strip(), password.strip(), email.strip(), favorite_animal.strip()):
            response = self.aes.encrypt(b"Signup successful")
            client_socket.sendall(struct.pack('>I', len(response)) + response)
        else:
            response = self.aes.encrypt(b"Signup failed - Username already exists")
            client_socket.sendall(struct.pack('>I', len(response)) + response)

    def handle_signin(self, client_socket, message):
        """
        Handle user sign-in.

        Parameters:
        client_socket (socket): The client socket.
        message (str): The sign-in message.
        """
        _, username, password = message.split(":")
        if self.validate_user(username.strip(), password.strip()):
            response = self.aes.encrypt(b"Signin successful")
            client_socket.sendall(struct.pack('>I', len(response)) + response)
        else:
            response = self.aes.encrypt(b"Signin failed - Invalid credentials")
            client_socket.sendall(struct.pack('>I', len(response)) + response)

    def handle_bpm_set(self, message):
        """Handle setting BPM (beats per minute)."""
        self.bpm = int(message.split(": ")[1])

    def handle_open_file(self, message):
        """Handle opening an audio file."""
        self.filepath = message.split(": ")[1]

    def handle_process_audio(self, client_socket):
        """Handle processing the audio file."""
        print("Processing audio... Please wait.")
        identifier = Identify_Chords.ChordIdentifier(self.model_path, self.bpm)
        list_of_chords = identifier.predict_chord(self.filepath)

        chords_json = json.dumps(list_of_chords)
        encrypted_response = self.aes.encrypt(chords_json.encode())
        client_socket.sendall(struct.pack('>I', len(encrypted_response)) + encrypted_response)

    def validate_user(self, username, password):
        """
        Validate user credentials.

        Parameters:
        username (str): The username.
        password (str): The password.

        Returns:
        bool: True if the user credentials are valid, False otherwise.
        """
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        conn = sqlite3.connect('user_db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
        account = c.fetchone()
        conn.close()
        return bool(account)

    def insert_user(self, username, password, email, favorite_animal):
        """
        Insert a new user into the database.

        Parameters:
        username (str): The username.
        password (str): The password.
        email (str): The email address.
        favorite_animal (str): The user's favorite animal.

        Returns:
        bool: True if the user was successfully inserted, False otherwise.
        """
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        try:
            conn = sqlite3.connect('user_db.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, email, favorite_animal) VALUES (?, ?, ?, ?)",
                      (username, hashed_password, email, favorite_animal))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"Error inserting new user: {e}")
            return False
        finally:
            conn.close()

    def start(self):
        """Start the server and listen for incoming connections."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(("0.0.0.0", self.port))
            server_socket.listen()
            print(f"Server listening for connections on {self.host}:{self.port}...")

            while True:
                client_socket, addr = server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client_connection, args=(client_socket, addr))
                client_thread.start()


if __name__ == "__main__":
    server = Server()
    server.start()
