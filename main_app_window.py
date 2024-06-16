import socket
import struct
import json
from tkinter import filedialog, simpledialog, messagebox
import tkinter as tk
import pygame
import threading
import time
import os
from aes import AESEncryption

class AudioPlayerApp(tk.Tk):
    """
    This class creates a GUI application for playing audio files using Tkinter and pygame.
    It also handles encryption and communication with a server for various actions.
    """

    def __init__(self, client_socket=None):
        """Initialize the audio player application."""
        super().__init__()
        self.title("Audio Player with Tkinter")
        self.geometry("500x600")
        self.configure(bg='#282a36')

        # Initialize instance variables
        self.client_socket = client_socket
        self.aes = None  # This will be set from AuthenticatedAudioPlayerApp
        self.file_path = None
        self.timer_running = False
        self.start_time = 0
        self.elapsed_time = 0
        self.playing = False
        self.paused = False
        self.bpm = None
        self.capo_position = 0
        self.current_chord = "N/A"
        self.next_chord = "N/A"
        self.pause_start_time = 0
        self.total_pause_duration = 0
        self.chords_timeline = []
        self.audio_processed = False

        # Initialize client socket if not provided
        if self.client_socket is None:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect_to_server()

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        self.setup_widgets()
        self.check_audio_end()

    def setup_widgets(self):
        """Create and pack the GUI widgets."""
        self.open_button = tk.Button(self, text="Open WAV File", command=self.open_file, bg='#6272a4', fg='white')
        self.open_button.pack(pady=10)

        self.start_continue_button = tk.Button(self, text="Start", command=self.toggle_audio, bg='#6272a4', fg='white')
        self.start_continue_button.pack(pady=10)

        self.pause_button = tk.Button(self, text="Pause", command=self.pause_audio, bg='#6272a4', fg='white')
        self.pause_button.pack(pady=10)

        self.restart_button = tk.Button(self, text="Restart", command=self.restart_audio, bg='#6272a4', fg='white')
        self.restart_button.pack(pady=10)

        self.bpm_button = tk.Button(self, text="Enter BPM", command=self.enter_bpm, bg='#6272a4', fg='white')
        self.bpm_button.pack(pady=10)

        self.capo_button = tk.Button(self, text="Select Capo", command=self.select_capo, bg='#6272a4', fg='white')
        self.capo_button.pack(pady=10)

        self.elapsed_time_label = tk.Label(self, text="Elapsed Time: 0.00s", bg='#282a36', fg='white')
        self.elapsed_time_label.pack(pady=10)

        self.current_chord_label = tk.Label(self, text=f"Current Chord: {self.current_chord}", bg='#282a36', fg='white')
        self.current_chord_label.pack(pady=5)

        self.next_chord_label = tk.Label(self, text=f"Next Chord: {self.next_chord}", bg='#282a36', fg='white')
        self.next_chord_label.pack(pady=5)

        self.quit_button = tk.Button(self, text="Quit", command=self.quit_application, bg='#6272a4', fg='white')
        self.quit_button.pack(pady=10)

        self.reset_button = tk.Button(self, text="Reset", command=self.reset_audio, bg='#ff5555', fg='white')
        self.reset_button.pack(pady=10)

        self.process_button = tk.Button(self, text="Process", command=self.process_audio, bg='#6272a4', fg='white')
        self.process_button.pack(pady=10)

    def connect_to_server(self):
        """
        Connect to the server and handle the encryption setup by exchanging keys.
        """
        try:
            self.client_socket.connect(("localhost", 65433))
            print("Connected to server")

            # Receive public key length and key
            public_key_length = struct.unpack('>I', self.recv_exactly(4))[0]
            print(f"Received public key length: {public_key_length}")

            public_key_pem = self.recv_exactly(public_key_length)
            print("Received public key")

            # Generate AES key and encrypt it with the server's public key
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

    def send_action_to_server(self, message_type, action):
        """
        Encrypt and send an action message to the server.
        """
        if self.aes is None:
            messagebox.showerror("Encryption Error", "AES encryption is not initialized.")
            print("AES encryption is not initialized.")
            return
        action_encoded = self.aes.encrypt(action.encode())
        header = struct.pack('>II', message_type, len(action_encoded))
        self.client_socket.sendall(header + action_encoded)
        print(f"Sent action to server: {action}")

    def send_non_essential_action(self, action):
        """Send a non-essential action message to the server."""
        self.send_action_to_server(0, action)  # Use message type 0 for non-essential actions

    def open_file(self):
        """Open a file dialog to select a WAV file and notify the server."""
        self.file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if self.file_path:
            if self.aes is None:
                messagebox.showerror("Encryption Error", "AES encryption is not initialized.")
                return
            self.send_action_to_server(4, "Open file: " + self.file_path)

    def process_audio(self):
        """
        Process the selected audio file and update the chords timeline.
        """
        if not self.file_path or not self.bpm:
            messagebox.showinfo("Process Audio", "Please select a file and enter BPM first.")
            return

        self.send_action_to_server(5, "process_audio")

        data_length = struct.unpack('>I', self.recv_exactly(4))[0]
        encrypted_response = self.recv_exactly(data_length)
        response = self.aes.decrypt(encrypted_response).decode()
        try:
            list_of_chords = json.loads(response)
            self.chords_timeline = list_of_chords
            self.audio_processed = True
            print("Audio processing completed")
            messagebox.showinfo("Process Audio", "Audio processing completed.")
        except json.JSONDecodeError:
            messagebox.showerror("Process Audio", "Error decoding the processed chords.")

    def toggle_audio(self):
        """Start, pause, or continue audio playback based on the current state."""
        if not self.playing and not self.paused:
            if self.file_path and self.bpm is not None:
                if self.audio_processed:
                    self.start_audio()
                else:
                    messagebox.showinfo("Error", "Please process the audio before starting.")
            else:
                messagebox.showinfo("Error", "Please select a file and enter BPM first.")
        elif self.paused:
            self.continue_audio()
        else:
            self.pause_audio()

    def start_audio(self):
        """Start audio playback."""
        self.play_sound(self.file_path)
        self.start_continue_button.config(text="Continue")
        print("Starting audio playback")
        self.send_non_essential_action("Start_audio")

    def pause_audio(self):
        """Pause audio playback."""
        if self.playing:
            pygame.mixer.music.pause()
            self.paused = True
            self.playing = False
            self.timer_running = False
            self.pause_start_time = time.time()
            self.send_non_essential_action("pause_audio")

    def continue_audio(self):
        """Continue audio playback."""
        if self.paused:
            pygame.mixer.music.unpause()
            self.playing = True
            self.paused = False
            self.timer_running = True
            self.total_pause_duration += time.time() - self.pause_start_time
            threading.Thread(target=self.update_elapsed_time, daemon=True).start()
            self.send_non_essential_action("Continue_audio")

    def restart_audio(self):
        """Restart audio playback from the beginning."""
        if self.file_path and self.bpm is not None:
            pygame.mixer.music.stop()
            self.play_sound(self.file_path)
            self.send_non_essential_action("Restart_audio")

    def enter_bpm(self):
        """Prompt the user to enter the BPM (beats per minute)."""
        bpm = simpledialog.askinteger("BPM", "Enter the BPM:", minvalue=1, maxvalue=300)
        if bpm is not None:
            self.bpm = bpm
            self.send_action_to_server(3, f"BPM set to: {self.bpm}")

    def select_capo(self):
        """Prompt the user to select the capo position."""
        capo_position = simpledialog.askinteger("Capo Position", "Select Capo Position (0-11):", minvalue=0, maxvalue=11)
        if capo_position is not None:
            self.capo_position = capo_position
            self.send_action_to_server(0, f"Capo position set to: {self.capo_position}")

    def play_sound(self, file_path):
        """Load and play the sound file."""
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        self.playing = True
        self.paused = False
        self.start_time = time.time()
        self.timer_running = True
        threading.Thread(target=self.update_elapsed_time, daemon=True).start()

    def update_elapsed_time(self):
        """Update the elapsed time and chord display while the audio is playing."""
        while self.timer_running:
            if self.playing:
                current_time = time.time()
                self.elapsed_time = current_time - self.start_time - self.total_pause_duration
                elapsed_str = f"Elapsed Time: {self.elapsed_time:.2f}s"
                self.elapsed_time_label.config(text=elapsed_str)
                self.update_chord_display()
            time.sleep(0.01)

    def quit_application(self):
        """Send quit action to the server and close the application."""
        self.send_action_to_server(6, "Quit")
        self.destroy()

    def reset_audio(self):
        """Reset the audio player state and GUI."""
        self.send_non_essential_action("Reset")
        pygame.mixer.music.stop()
        self.playing = False
        self.paused = False
        self.timer_running = False
        self.bpm = None
        self.file_path = None
        self.audio_processed = False

        self.elapsed_time_label.config(text="Elapsed Time: 0.00s")
        self.current_chord_label.config(text="Current Chord: N/A")
        self.next_chord_label.config(text="Next Chord: N/A")
        self.start_continue_button.config(text="Start")
        self.open_file()
        self.enter_bpm()
        self.chords_timeline = []

    def update_chord_display(self):
        """Update the display of the current and next chords based on the elapsed time."""
        elapsed_time = self.elapsed_time
        current_chord, next_chord = "N/A", "N/A"

        for i, (chord, start_time) in enumerate(self.chords_timeline):
            next_chord_start_time = self.chords_timeline[i + 1][1] if i + 1 < len(self.chords_timeline) else float('inf')
            if start_time <= elapsed_time < next_chord_start_time:
                current_chord = chord
                next_chord = self.chords_timeline[i + 1][0] if i + 1 < len(self.chords_timeline) else "N/A"
                break

        self.current_chord_label.config(text=f"Current Chord: {current_chord}")
        self.next_chord_label.config(text=f"Next Chord: {next_chord}")

    def check_audio_end(self):
        """Continuously check if the audio has finished playing and reset the player if it has."""
        def check():
            while True:
                time.sleep(1)
                if not pygame.mixer.music.get_busy() and self.playing:
                    self.reset_audio()
                    break

        threading.Thread(target=check, daemon=True).start()
