import os
import numpy as np
import soundfile as sf
import librosa
import pandas as pd
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from core.model_strategies import get_model_strategy

class AudioAnalysisWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_file, model_filename, output_dir):
        super().__init__()
        self.audio_file = audio_file
        self.model_filename = model_filename
        self.output_dir = output_dir

    def emit_progress(self, pct, msg):
        """Callback trimis către model pentru a comunica cu GUI-ul."""
        self.progress.emit(pct, msg)

    def run(self):
        try:
            audio_path_obj = Path(self.audio_file)
            file_stem = audio_path_obj.stem
            parent_folder = audio_path_obj.parent.name # Preluăm numele folderului părinte
            
            run_dir = Path(self.output_dir) / file_stem
            
            # Creare ierarhie output
            hfc_dir = run_dir / "HFC"
            lfc_dir = run_dir / "LFC"
            hfc_dir.mkdir(parents=True, exist_ok=True)
            lfc_dir.mkdir(parents=True, exist_ok=True)

            # 1. INIȚIALIZĂM STRATEGIA CORECTĂ DINAMIC
            model_strategy = get_model_strategy(self.model_filename)
            
            # 2. RULĂM ANALIZA (Extrage DataFrame-ul cu vocalizările)
            df_results = model_strategy.analyze(self.audio_file, self.emit_progress)

            if df_results.empty:
                self.progress.emit(100, "Nu s-au găsit vocalizări.")
                self.finished.emit(str(run_dir))
                return

            # 3. CROP ȘI SALVARE (Logica din process_single_file)
            self.progress.emit(85, "Se decupează sunetele...")
            
            file_names = []
            padding_sec = 0.5 # Padding de 0.5s[cite: 10]
            target_sr = 16000

            # Preluăm informațiile despre fișierul original pentru a calcula corect durata și cadrele[cite: 10]
            info = sf.info(self.audio_file)
            original_sr = info.samplerate
            total_duration_sec = info.frames / original_sr

            for index, row in df_results.iterrows():
                formatted_num = str(index + 1).zfill(4)
                label_prefix = row['label']

                # Numele fișierului exact cum era în scriptul original[cite: 10]
                wav_file_name = f"{label_prefix}_{formatted_num}_{file_stem}_{parent_folder}.wav"
                file_names.append(wav_file_name)

                # Rutare în folderul corect bazat pe etichetă
                if "HFC" in label_prefix:
                    target_dir = hfc_dir
                else:
                    target_dir = lfc_dir

                # Calculăm limitele exacte cu padding[cite: 10]
                tmin_pad = max(0, row['tmin'] - padding_sec)
                tmax_pad = min(total_duration_sec, row['tmax'] + padding_sec)

                start_frame = int(tmin_pad * original_sr)
                frames_to_read = int((tmax_pad - tmin_pad) * original_sr)

                # Citim doar porțiunea necesară[cite: 10]
                audio_chunk, _ = sf.read(self.audio_file, start=start_frame, frames=frames_to_read)

                # Convertim la mono dacă are mai multe canale[cite: 10]
                if len(audio_chunk.shape) > 1:
                    audio_chunk = np.mean(audio_chunk, axis=1)

                # Resample la 16kHz dacă e nevoie[cite: 10]
                if original_sr != target_sr:
                    audio_chunk = librosa.resample(audio_chunk, orig_sr=original_sr, target_sr=target_sr)

                # Salvăm fișierul decupat
                save_path = target_dir / wav_file_name
                sf.write(save_path, audio_chunk, target_sr)

            self.progress.emit(95, "Se generează tabelul cu date...")

            # Inserăm numele fișierelor tăiate la începutul tabelului[cite: 10]
            df_results.insert(0, 'File', file_names)
            
            # Generăm fișierul Excel
            excel_path = run_dir / f"{file_stem}_analiza.xlsx"
            df_results.to_excel(excel_path, index=False)

            self.progress.emit(100, "Analiză completă!")
            self.finished.emit(str(run_dir))
            
        except Exception as e:
            self.error.emit(str(e))