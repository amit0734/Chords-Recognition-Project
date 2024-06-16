from joblib import load
import numpy as np
import librosa


class ChordIdentifier:
    """
    This class identifies chords in an audio file using a pre-trained machine learning model.
    """

    def __init__(self, model_path, bpm):
        """
        Initialize the ChordIdentifier with a pre-trained model and beats per minute (BPM).

        Parameters:
        model_path (str): Path to the pre-trained model file.
        bpm (int): Beats per minute of the audio track.
        """
        self.model = load(model_path)  # Load the pre-trained model
        self.bpm = bpm
        self.segment_duration = (60 / bpm) * 4  # Duration of a 4/4 beat in seconds

    @staticmethod
    def extract_features(audio_segment, sample_rate):
        """
        Extract MFCC features from an audio segment.

        Parameters:
        audio_segment (np.ndarray): The audio segment.
        sample_rate (int): The sample rate of the audio.

        Returns:
        np.ndarray: Processed MFCC features.
        """
        try:
            mfccs = librosa.feature.mfcc(y=audio_segment, sr=sample_rate, n_mfcc=40)
            mfccs_processed = np.mean(mfccs.T, axis=0)
        except Exception as e:
            print("Error encountered while parsing segment.")
            print("Error details:", e)
            return None
        return mfccs_processed

    def predict_chord(self, audio_file):
        """
        Predict the chords in the given audio file.

        Parameters:
        audio_file (str): Path to the audio file.

        Returns:
        list: List of tuples with predicted chords and their start times.
        """
        audio, sample_rate = librosa.load(audio_file, res_type='kaiser_fast')  # Load the audio file

        total_duration = librosa.get_duration(y=audio, sr=sample_rate)  # Get total duration of the audio
        segments = int(total_duration // self.segment_duration)  # Calculate the number of segments

        chord_times = []  # List to store each chord and its appearance time

        for segment in range(segments):
            segment_start_time = segment * self.segment_duration
            start_sample = int(segment_start_time * sample_rate)
            end_sample = int((segment + 1) * self.segment_duration * sample_rate)
            audio_segment = audio[start_sample:end_sample]

            features = self.extract_features(audio_segment, sample_rate)
            if features is not None:
                features = np.array([features])
                prediction = self.model.predict(features)[0]
                if len(chord_times) == 0:
                    chord_times.append((prediction, segment_start_time))  # Add chord and its start time
                elif chord_times[-1][0] != prediction:
                    chord_times.append((prediction, segment_start_time))  # Add chord and its start time
            else:
                print(f"Segment {segment + 1}: Could not process the audio segment.")

        return chord_times
