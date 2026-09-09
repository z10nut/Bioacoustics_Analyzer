import numpy as np
import soundfile as sf
import librosa
import pandas as pd
import tensorflow as tf
from scipy.signal import butter, filtfilt

# --- Bandpass Filter ---
def butter_bandpass_filter(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_bandpass_filter(data, fs, lowcut=80.0, highcut=2500.0, order=4):
    b, a = butter_bandpass_filter(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y

def extract_embedding(audio_segment, model):
    if len(audio_segment) == 0:
        return None
    waveform = tf.convert_to_tensor(audio_segment, dtype=tf.float32)
    _ , embeddings, _ = model(waveform)
    if embeddings.shape[0] == 0:
        return None
    return np.mean(embeddings.numpy(), axis=0)

def run_yamnet_svm_detection(audio_path, yamnet_model, svm_model, progress_callback):
    target_sr = 16000
    file_info = sf.info(audio_path)
    original_sr = file_info.samplerate
    total_duration_sec = file_info.frames / original_sr

    window_length_sec = 1.0
    window_stride_sec = 0.25

    raw_detections = []
    start_sec = 0.0

    total_steps = int(total_duration_sec / window_stride_sec)
    current_step = 0

    progress_callback(20, "Scanning audio for vocalizations...")

    while start_sec + window_length_sec <= total_duration_sec:
        start_frame = int(start_sec * original_sr)
        frames_to_read = int(window_length_sec * original_sr)

        chunk, _ = sf.read(audio_path, start=start_frame, frames=frames_to_read)

        if len(chunk.shape) > 1:
            chunk = np.mean(chunk, axis=1)

        if original_sr != target_sr:
            chunk = librosa.resample(chunk, orig_sr=original_sr, target_sr=target_sr)

        chunk = apply_bandpass_filter(chunk, target_sr, lowcut=80.0, highcut=2500.0, order=4)
        emb = extract_embedding(chunk, yamnet_model)

        if emb is not None:
            decision_scores = svm_model.decision_function(emb.reshape(1, -1))[0]
            best_class_idx = np.argmax(decision_scores)
            best_score = decision_scores[best_class_idx]
            predicted_class = svm_model.classes_[best_class_idx]

            CONFIDENCE_THRESHOLD = 0.5
            if best_score > CONFIDENCE_THRESHOLD and predicted_class in [1, 2, 3, 4]:
                raw_detections.append((start_sec, start_sec + window_length_sec, predicted_class))

        start_sec += window_stride_sec
        current_step += 1

        if current_step % 10 == 0:
            pct = 20 + int((current_step / total_steps) * 50)
            progress_callback(pct, f"Scanning {int(start_sec)}s / {int(total_duration_sec)}s")

    if not raw_detections:
        return pd.DataFrame(columns=['tmin', 'tmax', 'label'])

    progress_callback(75, "Post-processing detections...")

    consolidated_detections = []
    current_tmin, current_tmax, current_class = raw_detections[0]
    gap_tolerance = 0.0

    for tmin, tmax, cls in raw_detections[1:]:
        if tmin - current_tmax <= gap_tolerance and cls == current_class:
            current_tmax = tmax
        else:
            consolidated_detections.append((current_tmin, current_tmax, current_class))
            current_tmin, current_tmax, current_class = tmin, tmax, cls

    consolidated_detections.append((current_tmin, current_tmax, current_class))

    class_map = {1: 'Calve_HFC', 2: 'Calve_LFC', 3: 'Cow_HFC', 4: 'Cow_LFC'}
    df_results = pd.DataFrame(consolidated_detections, columns=['tmin', 'tmax', 'class_id'])
    df_results['label'] = df_results['class_id'].map(class_map)
    df_results = df_results.drop(columns=['class_id'])

    return df_results