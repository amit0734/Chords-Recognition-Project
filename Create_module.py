import pandas as pd
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from joblib import dump


class ChordClassifier:
    """
    This class trains a chord classification model using a dataset of audio files and their corresponding labels.
    """

    def __init__(self, csv_path):
        """
        Initialize the ChordClassifier with the path to the CSV file containing the dataset.

        Parameters:
        csv_path (str): Path to the CSV file containing the dataset.
        """
        self.csv_path = csv_path
        self.model = None

    def extract_features(self, audio_file):
        """
        Extract MFCC features from an audio file.

        Parameters:
        audio_file (str): Path to the audio file.

        Returns:
        np.ndarray: Processed MFCC features.
        """
        try:
            audio, sample_rate = librosa.load(audio_file, res_type='kaiser_fast')
            mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=40)
            mfccs_processed = np.mean(mfccs.T, axis=0)
            return mfccs_processed
        except Exception as e:
            print("Error encountered while parsing audio file:", audio_file)
            print("Error details:", e)
            return None

    def load_data(self):
        """
        Load the dataset from the CSV file and extract features and labels.

        Returns:
        tuple: A tuple containing the features and labels as numpy arrays.
        """
        df = pd.read_csv(self.csv_path)
        features = []
        labels = []

        for index, row in df.iterrows():
            if row['label'] == 'Bdim':  # Skip records where the label is 'Bdim'
                continue
            audio_file = row['filename']
            feature = self.extract_features(audio_file)
            if feature is not None:
                features.append(feature)
                labels.append(row['label'])

        return np.array(features), np.array(labels)

    def train_model(self):
        """
        Train the chord classification model using the dataset.
        """
        X, y = self.load_data()  # Load features and labels
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model = RandomForestClassifier(n_estimators=100)  # Initialize the model
        self.model.fit(X_train, y_train)  # Train the model

        # Evaluate the model
        predictions = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        print("Accuracy:", accuracy)

    def save_model(self, model_path):
        """
        Save the trained model to a file.

        Parameters:
        model_path (str): Path to the file where the model will be saved.
        """
        if self.model:
            dump(self.model, model_path)
        else:
            print("No model has been trained yet.")


# Example usage:
csv_path = r'C:\Users\Amit Sibony\Downloads\chords_dataset.csv'
classifier = ChordClassifier(csv_path)
classifier.train_model()
model_path = r'C:\Users\Amit Sibony\Downloads\trained_model2.joblib'
classifier.save_model(model_path)
