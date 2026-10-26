import os
import logging
import numpy as np
import soundfile as sf
import librosa
import pandas as pd
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from core.model_strategies import get_model_strategy

logger = logging.getLogger(__name__)

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
        """Emit progress signal with percentage and message."""
        self.progress.emit(pct, msg)

    def run(self):
        try:
            logger.info(f"Starting analysis for {self.audio_file} using model {self.model_filename}")

            audio_path_obj = Path(self.audio_file)
            file_stem = audio_path_obj.stem
            parent_folder = audio_path_obj.parent.name 
            
            run_dir = Path(self.output_dir) / file_stem
            detections_dir = run_dir / "Detections"
            detections_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Initializing model strategy.")
            model_strategy = get_model_strategy(self.model_filename)
            
            df_results = model_strategy.analyze(self.audio_file, self.emit_progress)

            if df_results.empty:
                logger.warning(f"No vocalizations detected in the audio file: {self.audio_file}.")
                self.progress.emit(100, "Could not detect any vocalizations in the audio file.")
                self.finished.emit(str(run_dir))
                return

            self.progress.emit(85, "Processing detected vocalizations...")
            logger.info(f"Extracting {len(df_results)} detected vocalizations to '{detections_dir}'.")

            info = sf.info(self.audio_file)
            original_sr = info.samplerate
            total_duration_sec = info.frames / original_sr
            
            file_names = []
            padding_sec = 0.5
            target_sr = 16000

            for index, row in df_results.iterrows():
                try:
                    formatted_num = str(index + 1).zfill(4)
                    label_prefix = row.get('label', 'Vocalization')

                    wav_file_name = f"{label_prefix}_{formatted_num}_{file_stem}_{parent_folder}.wav"
                    file_names.append(wav_file_name)

                    tmin_pad = max(0, row['tmin'] - padding_sec)
                    tmax_pad = min(total_duration_sec, row['tmax'] + padding_sec)

                    save_path = detections_dir / wav_file_name

                    self._extract_and_save_chunk(
                        tmin_pad, tmax_pad, original_sr, target_sr, save_path
                    )
                except Exception as e:
                    logger.error(f"Error processing vocalization {index + 1}: {e}")
                    self.error.emit(f"Error processing vocalization {index + 1}: {e}")

            self.progress.emit(95, "Generating Excel report...")
            df_results.insert(0, 'File', file_names)

            excel_path = run_dir / f"{file_stem}_analysis.xlsx"
            df_results.to_excel(excel_path, index=False)
            logger.info(f"Saved analysis results to Excel file: {excel_path}")

            self.progress.emit(100, "Analysis complete!")
            self.finished.emit(str(run_dir))
            logger.info(f"AudioAnalysisWorker finished successfully for {self.audio_file}. Results saved in {run_dir}")

        except Exception as e:
            logger.exception(f"An error occurred during audio analysis: {e}")
            self.error.emit(f"An error occurred during audio analysis: {e}")

    def _extract_and_save_chunk(self, tmin, tmax, original_sr, target_sr, save_path):
        """Extract a chunk of audio and save it as a WAV file."""
        start_frame = int(tmin * original_sr)
        frames_to_read = int((tmax - tmin) * original_sr)

        audio_chunk, _ = sf.read(self.audio_file, start=start_frame, frames=frames_to_read)

        if len(audio_chunk.shape) > 1:
            audio_chunk = np.mean(audio_chunk, axis=1)

        if original_sr != target_sr:
            audio_chunk = librosa.resample(audio_chunk, orig_sr=original_sr, target_sr=target_sr)

        sf.write(save_path, audio_chunk, target_sr)