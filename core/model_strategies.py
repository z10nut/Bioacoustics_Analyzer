import os
import sys
import importlib.util
import logging
import joblib
from abc import ABC, abstractmethod
from core.detection_engine import run_yamnet_svm_detection

logger = logging.getLogger(__name__)

# Base class for acoustic models
class BaseAcousticModel(ABC):
    def __init__(self, model_path=None):
        self.model_path = model_path

    @abstractmethod
    def analyze(self, audio_path, progress_callback):
        """Analyze the audio file and return a DataFrame with detection results."""
        pass

# YAMNet + SVM model
class YamnetSvmModel(BaseAcousticModel):
    def analyze(self, audio_path, progress_callback):
        import tensorflow_hub as hub

        progress_callback(5, "Downloading YAMNet model...")
        logger.info("Loading YAMNet feature extractor from tfhub...")
        yamnet_model = hub.load('https://tfhub.dev/google/yamnet/1')

        progress_callback(15, "Loading SVM classification model...")
        logger.info(f"Loading SVM model from {self.model_path}")
        svm_model = joblib.load(self.model_path)

        logger.info("Starting YAMNetSvmModel analysis")
        return run_yamnet_svm_detection(audio_path, yamnet_model, svm_model, progress_callback)

def get_model_strategy(model_filename):
    """Factory function to return the appropriate model strategy based on the model filename."""
    model_path = os.path.join("models", model_filename)

    if not os.path.exists(model_path):
        logger.error(f"Model file not found: {model_path}")
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Determine the model type based on the file extension
    if model_filename.lower().endswith(".pkl"):
        logger.info(f"Instantiating build-in YamnetSvmModel for '{model_filename}'")
        return YamnetSvmModel(model_path)
    
    elif model_filename.lower().endswith(".py"):
        logger.info(f"Detected custom Python script. Attempting dynamic import: {model_path}")
        return _load_custom_python_plugin(model_path)
    
    else:
        logger.error(f"Unsupported model file type: {model_filename}")
        raise ValueError(f"Unsupported model file type: {model_filename}")

def _load_custom_python_plugin(script_path):
    """
    Dynamically load a custom Python file that does not belong to PYTHONPATH.
    The script must define a class that inherits from BaseAcousticModel and implement the analyze method.
    """
    module_name = os.path.splitext(os.path.basename(script_path))[0]

    try:
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        custom_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = custom_module
        spec.loader.exec_module(custom_module)

        # Search for a class that inherits from BaseAcousticModel
        for attr_name in dir(custom_module):
            attr = getattr(custom_module, attr_name)

            if isinstance(attr, type) and issubclass(attr, BaseAcousticModel) and attr is not BaseAcousticModel:
                logger.info(f"Successfully loaded custom plugin class '{attr_name}' from '{script_path}'")
                return attr(model_path=script_path)

        raise ValueError("No class inheriting from BaseAcousticModel was found in the script.")
    
    except Exception as e:
        logger.error(f"Failed to load custom plugin from '{script_path}': {e}")
        raise RuntimeError(f"Failed to load custom plugin from '{script_path}': {e}")