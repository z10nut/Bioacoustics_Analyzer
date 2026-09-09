import os
import joblib
from abc import ABC, abstractmethod
from core.detection_engine import run_yamnet_svm_detection

class BaseAcousticModel(ABC):
    def __init__(self, model_path):
        self.model_path = model_path

    @abstractmethod
    def analyze(self, audio_path, progress_callback):
        pass

class YamnetSvmModel(BaseAcousticModel):
    def analyze(self, audio_path, progress_callback):
        import tensorflow_hub as hub
        
        progress_callback(5, "Downloading YAMNet model...")
        yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
        
        progress_callback(15, "Loading SVM model...")
        svm_model = joblib.load(self.model_path)
        
        return run_yamnet_svm_detection(audio_path, yamnet_model, svm_model, progress_callback)

def get_model_strategy(model_filename):
    model_path = os.path.join("models", model_filename)
    if "svm" in model_filename.lower() or model_filename.endswith(".pkl"):
        return YamnetSvmModel(model_path)
    else:
        raise ValueError(f"Unknown model type: {model_filename}")