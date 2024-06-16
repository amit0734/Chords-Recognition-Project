import socket
import struct
from tkinter import messagebox
import tkinter as tk
import os
from aes import AESEncryption
from rsa import RSAEncryption
from main_app_window import AudioPlayerApp

class AuthenticatedAudioPlayerApp(tk.Tk):
    """
    This class handles the authentication window for the audio player application.
    It manages the sign-in and sign-up process and initializes the main application window upon successful authentication.
    """

    def __init__(self):
        """Initialize the authentication window and set up the socket connection."""
        super().__init__()
        self.title("Authentication")
        self.geometry("300x200")
        self.configure(bg='#282a36')

        # Initialize the socket and encryption variables
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rsa = RSAEncryption()
        self.aes_key = None
        self.aes = None
        try:
            self.connect_to_auth_server()
            self.setup_auth_widgets()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Unable to connect to server: {e}")
            self.destroy()

    def connect_to_auth_server(self):
        """
        Connect to the authentication server and perform key exchange for AES encryption.
        """
        try:
            self.client_socket.connect(("localhost", 65433))
            print("Connected to auth server")

            # Receive the length of the server's public key
            public_key_length = struct.unpack('>I', self.recv_exactly(4))[0]
            print(f"Received public key length: {public_key_length}")

            # Receive the server's public key
            public_key_pem = self.recv_exactly(public_key_length)
            print("Received public key")

            # Generate an AES key and encrypt it with the server's public key
            self.aes_key = os.urandom(32)
            self.aes = AESEncryption(self.aes_key)
            print("Generated AES key")

            encrypted_aes_key = self.rsa.encrypt(self.aes_key, public_key_pem)
            print("Encrypted AES key")

            # Send the encrypted AES key to the server
            self.client_socket.sendall(struct.pack('>I', len(encrypted_aes_key)) + encrypted_aes_key)
            print("Sent encrypted AES key to server")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Unable to connect to server: {e}")
            self.destroy()

    def recv_exactly(self, n):
        """
        Receive exactly n bytes from the socket.
        """
        data = b''
        while len(data) < n:
            packet = self.client_socket.recv(n - len(data))
            if not packet:
                raise ConnectionError("Socket connection broken")
            data += packet
        return data

    def setup_auth_widgets(self):
        """Set up the authentication GUI widgets."""
        tk.Label(self, text="Username:", bg='#282a36', fg='white').pack(pady=(10, 0))
        self.username_entry = tk.Entry(self, bg='#44475a', fg='white', insertbackground='white')
        self.username_entry.pack(pady=(0, 10))

        tk.Label(self, text="Password:", bg='#282a36', fg='white').pack(pady=(0, 0))
        self.password_entry = tk.Entry(self, show="*", bg='#44475a', fg='white', insertbackground='white')
        self.password_entry.pack(pady=(0, 20))

        tk.Button(self, text="Sign In", command=self.sign_in, bg='#6272a4', fg='white').pack()

        self.sign_up_label = tk.Label(self, text="Don't have an account? Sign Up", fg='#ff79c6', cursor="hand2", bg='#282a36')
        self.sign_up_label.pack(pady=(10, 0))
        self.sign_up_label.bind("<Button-1>", lambda e: self.open_sign_up_window())

    def open_sign_up_window(self):
        """Open the sign-up window."""
        self.signup_window = tk.Toplevel(self)
        self.signup_window.title("Sign Up")
        self.signup_window.geometry("300x350")
        self.signup_window.configure(bg='#282a36')

        tk.Label(self.signup_window, text="Username:", bg='#282a36', fg='white').grid(row=0, column=0, padx=10, pady=5)
        self.signup_username = tk.Entry(self.signup_window, bg='#44475a', fg='white', insertbackground='white')
        self.signup_username.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self.signup_window, text="Password:", bg='#282a36', fg='white').grid(row=1, column=0, padx=10, pady=5)
        self.signup_password = tk.Entry(self.signup_window, show="*", bg='#44475a', fg='white', insertbackground='white')
        self.signup_password.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.signup_window, text="Confirm Password:", bg='#282a36', fg='white').grid(row=2, column=0, padx=10, pady=5)
        self.signup_confirm_password = tk.Entry(self.signup_window, show="*", bg='#44475a', fg='white', insertbackground='white')
        self.signup_confirm_password.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self.signup_window, text="Email:", bg='#282a36', fg='white').grid(row=3, column=0, padx=10, pady=5)
        self.signup_email = tk.Entry(self.signup_window, bg='#44475a', fg='white', insertbackground='white')
        self.signup_email.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(self.signup_window, text="Favorite Animal:", bg='#282a36', fg='white').grid(row=4, column=0, padx=10, pady=5)
        self.signup_favorite_animal = tk.Entry(self.signup_window, bg='#44475a', fg='white', insertbackground='white')
        self.signup_favorite_animal.grid(row=4, column=1, padx=10, pady=5)

        signup_submit_btn = tk.Button(self.signup_window, text="Submit", command=self.submit_sign_up, bg='#6272a4', fg='white')
        signup_submit_btn.grid(row=5, column=0, columnspan=2, pady=10)

    def submit_sign_up(self):
        """Submit the sign-up information to the server."""
        username = self.signup_username.get()
        password = self.signup_password.get()
        confirm_password = self.signup_confirm_password.get()
        email = self.signup_email.get()
        favorite_animal = self.signup_favorite_animal.get()

        if password != confirm_password:
            messagebox.showerror("Sign Up Failed", "Passwords do not match. Please try again.")
            return

        try:
            signup_request = f"signup:{username}:{password}:{email}:{favorite_animal}"
            self.send_action_to_server(1, signup_request)
            response_length = struct.unpack('>I', self.recv_exactly(4))[0]
            encrypted_response = self.recv_exactly(response_length)
            response = self.aes.decrypt(encrypted_response).decode()
            if "successful" in response:
                messagebox.showinfo("Sign Up", "Sign up successful! You can now sign in.")
                self.signup_window.destroy()
            else:
                messagebox.showerror("Sign Up Failed", response)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Error during sign-up: {e}")

    def sign_in(self):
        """Submit the sign-in information to the server and start the main application if successful."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        try:
            signin_request = f"signin:{username}:{password}"
            self.send_action_to_server(2, signin_request)
            response_length = struct.unpack('>I', self.recv_exactly(4))[0]
            encrypted_response = self.recv_exactly(response_length)
            response = self.aes.decrypt(encrypted_response).decode()
            if "successful" in response:
                self.destroy()
                app = AudioPlayerApp(self.client_socket)
                app.aes = self.aes  # Ensure AES is passed to the main app
                app.mainloop()
            else:
                messagebox.showerror("Sign In Failed", response)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Error during sign-in: {e}")

    def send_action_to_server(self, message_type, action):
        """Encrypt and send an action message to the server."""
        if self.aes is None:
            messagebox.showerror("Encryption Error", "AES encryption is not initialized.")
            print("AES encryption is not initialized.")
            return
        action_encoded = self.aes.encrypt(action.encode())
        header = struct.pack('>II', message_type, len(action_encoded))
        self.client_socket.sendall(header + action_encoded)
        print(f"Sent action to server: {action}")

def start_main_app(client_socket):
    """Start the main audio player application."""
    app = AudioPlayerApp(client_socket)
    app.mainloop()

if __name__ == "__main__":
    auth_app = AuthenticatedAudioPlayerApp()
    auth_app.mainloop()
