from sign_in_window import AuthenticatedAudioPlayerApp

class MainApp:
    """
    This class serves as the entry point for the main application.
    It initializes and runs the authentication window.
    """

    def run(self):
        """Initialize and run the authentication window."""
        auth_app = AuthenticatedAudioPlayerApp()
        auth_app.mainloop()

if __name__ == "__main__":
    # Create an instance of MainApp and run the application
    MainApp().run()
