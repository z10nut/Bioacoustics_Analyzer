import os
import gc
import math
import logging
import numpy as np
import pandas as pd
import parselmouth
from parselmouth.praat import call
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

def detect_30_40hz_spike(sound):
    """
    Detects a spike in the 30-40 Hz frequency band.

    Args:
        sound (parselmouth.Sound): The sound object to analyze.
        
    Returns:
        bool: True if a spike is detected, False otherwise.
    """

    try:
        spectrum = sound.to_spectrum()
        frequencies = spectrum.xs()
        power = np.abs(spectrum.values)**2
        power = power[0]
        
        band_mask = (frequencies >= 30) & (frequencies <= 40)
        if not np.any(band_mask):
            return False
            
        band_power = power[band_mask]
        mean_power = np.mean(power)
        std_power = np.std(power)
        
        spike_threshold = mean_power + (3 * std_power)
        return bool(np.max(band_power) > spike_threshold)
    except Exception as e:
        logger.debug(f"Failed to detect 30-40Hz spike: {e}")
        return False

def calculate_modulations_fast(obj_type, obj, tier, duration):
    """
    Calculates modulation rate and extent for pitch or intensity.

    Args:
        obj_type (str): Type of the object ('pitch' or 'intensity').
        obj (parselmouth.Pitch or parselmouth.Intensity): The object to analyze
        tier (parselmouth.PitchTier or parselmouth.IntensityTier): The corresponding tier.
        duration (float): Duration of the sound in seconds.

    Returns:
        tuple: (variation_rate, modulation_rate, modulation_extent)
    """
    try:
        num_points = call(tier, "Get number of points")
        if obj_type == "pitch":
            vals = obj.selected_array['frequency']
            vals = np.where(vals == 0, np.nan, vals)
        else:
            vals = obj.values[0, :]
    except Exception as e:
        logger.exception(f"Failed to read points from tier {obj_type}: {e}")
        return np.nan, np.nan, np.nan
        
    infl_asc, infl_desc, variationtot = 0, 0, 0.0
    
    for current_frame in range(1, num_points):
        idx = current_frame - 1
        if idx - 1 < 0 or idx + 1 >= len(vals):
            continue
            
        val_before = vals[idx - 1]
        val_current = vals[idx]
        val_after = vals[idx + 1]
        
        if not math.isnan(val_current) and not math.isnan(val_before) and not math.isnan(val_after):
            # Check for inflection points
            if val_after > val_current and val_current <= val_before:
                infl_asc += 1
            elif val_after < val_current and val_current >= val_before:
                infl_desc += 1
            variationtot += abs(val_after - val_current)
            
    sum_infl = infl_asc + infl_desc
    var_rate = variationtot / duration if duration > 0 else 0
    mod_rate = (sum_infl / 2) / duration if duration > 0 else 0
    mod_extent = (variationtot / (sum_infl / 2)) if sum_infl > 0 else 0
    
    return var_rate, mod_rate, mod_extent

def calculate_wiener_entropy_faithful(sound, start_freq, end_freq, time_stepWE):
    """
    Computes the Wiener entropy over a specified frequency band.
    Lower values indicate more tonal sounds while higher values indicate noise.

    Args:
        sound (parselmouth.Sound): The sound object to analyze.
        start_freq (float): Lower bound of the band in Hz.
        end_freq (float): Upper bound of the band in Hz.
        time_stepWE (float): The time step for analysis in seconds.
    """
    if math.isnan(start_freq) or math.isnan(end_freq):
        return np.nan
        
    frame_duration = 0.01
    sampling_period = sound.dx
    duration = sound.get_total_duration()
    start_time = sound.xmin
    
    number_of_steps = math.floor((duration - frame_duration) / time_stepWE) + 1
    if number_of_steps <= 0:
        return np.nan
        
    sum_wiener_entropy = 0.0
    
    for _ in range(int(number_of_steps)):
        part = sound.extract_part(from_time=start_time, to_time=start_time+frame_duration, 
                                  window_shape=parselmouth.WindowShape.GAUSSIAN1, relative_width=1.0, preserve_times=True)
        start_time += time_stepWE
        
        spectrum = part.to_spectrum()
        df = spectrum.dx
        highest_freq = spectrum.xmax
        current_end_freq = min(end_freq, highest_freq)
        
        start_bin = round(start_freq / df + 1)
        end_bin = round(current_end_freq / df + 1)
        number_of_band_bins = int(end_bin - start_bin + 1)
        
        if number_of_band_bins <= 0:
            continue
            
        real_parts = spectrum.values[0, :]
        imag_parts = spectrum.values[1, :]
        powers = (real_parts / sampling_period)**2 + (imag_parts / sampling_period)**2
        
        total_bins = len(powers)
        sum_power_spectrum = 0.0
        sum_ln_power_spectrum = 0.0
        
        for b in range(start_bin, end_bin + 1):
            idx = b - 1
            p = powers[idx] if 0 <= idx < total_bins else 0.0
            sum_power_spectrum += p
            if p > 0:
                sum_ln_power_spectrum += math.log(p)
            
        arithmetic_mean = sum_power_spectrum / number_of_band_bins if number_of_band_bins > 0 else 0
        geometric_mean = math.exp(sum_ln_power_spectrum / number_of_band_bins) if number_of_band_bins > 0 else 0
        
        if arithmetic_mean > 0 and geometric_mean > 0:
            sum_wiener_entropy += math.log(geometric_mean / arithmetic_mean)
            
    return sum_wiener_entropy / number_of_steps

def extract_energy_parameters(sound):
    """
    Extracts energy parameters (Q25, Q50, Q75, Fpeak) from the sound object.

    Args:
        sound (parselmouth.Sound): The sound object to analyze.

    Returns:
        tuple: A tuple containing the extracted energy parameters (Q25, Q50, Q75, Fpeak).
    """
    spectrum = sound.to_spectrum()
    q50 = call(spectrum, "Get centre of gravity", 2)
        
    pass_filter = spectrum.copy()
    call(pass_filter, "Filter (pass Hann band)", 0, q50, 100)
    q25 = call(pass_filter, "Get centre of gravity", 2)
    
    stop_filter = spectrum.copy()
    call(stop_filter, "Filter (stop Hann band)", 0, q50, 100)
    q75 = call(stop_filter, "Get centre of gravity", 2)
    
    smooth_spec = call(spectrum, "Cepstral smoothing", 100)
    peaks = call(smooth_spec, "To SpectrumTier (peaks)")
    table = call(peaks, "Down to Table")
    
    num_rows = call(table, "Get number of rows")
    fpeak = np.nan
    max_pow = -float('inf')
    
    for i in range(1, num_rows + 1):
        try:
            p = float(call(table, "Get value", i, "pow(dB/Hz)"))
            if p > max_pow:
                max_pow = p
                fpeak = float(call(table, "Get value", i, "freq(Hz)"))
        except (ValueError, TypeError):
            continue
            
    return q25, q50, q75, fpeak

# UI QThread Class
class FeatureExtractionWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_dir, output_csv, animal_type, call_type="LFC"):
        super().__init__()
        self.input_dir = input_dir
        self.output_csv = output_csv
        self.animal_type = animal_type
        self.call_type = call_type

    def run(self):
        supported_extensions = ('.wav', '.aif', '.aiff', '.au')
        results = []

        logger.info(f"Starting feature extraction in directory: {self.input_dir}")
        
        if not os.path.isdir(self.input_dir):
            self.error.emit(f"Folder not found: {self.input_dir}")
            logger.error(f"Folder not found: {self.input_dir}")
            return
            
        all_files = os.listdir(self.input_dir)
        supported_files = [f for f in all_files if f.lower().endswith(supported_extensions)]
        total_files = len(supported_files)
        
        if total_files == 0:
            self.error.emit("No audio files found in the folder.")
            logger.warning("No audio files found in the folder.")
            return
            
        self.progress.emit(0, f"Initializing processing for {total_files} files...")
            
        for index, filename in enumerate(supported_files, start=1):
            pct = int((index / total_files) * 100)
            self.progress.emit(pct, f"[{index}/{total_files}] Processing: {filename}...")
            try:
                file_path = os.path.join(self.input_dir, filename)
                row_data = {"file": filename}
                
                if self.animal_type == 'calf':
                    metrics = self.analyze_calf(file_path)
                elif self.animal_type == 'cow':
                    metrics = self.analyze_cow(file_path, self.call_type)
                else:
                    metrics = {}
                    
                for key, val in metrics.items():
                    if key == "FM Extent (Hz)":
                        row_data[key] = val
                    elif isinstance(val, (float, int)) and not (isinstance(val, float) and math.isnan(val)):
                        row_data[key] = f"{val:.3f}"
                    else:
                        row_data[key] = val
                
                row_data["Comment"] = ""
                
                sound = parselmouth.Sound(file_path)
                row_data['Unvoicing_Required_Flag'] = detect_30_40hz_spike(sound)
                    
                results.append(row_data)
                
            except Exception as e:
                logger.warning(f"Skipped file {filename} due to error: {e}")
            finally:
                gc.collect()
                
        if results:
            self.progress.emit(95, "Saving Excel/CSV table...")
            df = pd.DataFrame(results)
            df.to_csv(self.output_csv, index=False)
            logger.info(f"Feature extraction completed. Results saved to: {self.output_csv}")

            self.progress.emit(100, "Processing completed successfully!")
            self.finished.emit(self.output_csv)
        else:
            logger.error("Feature extraction failed: No files could be analyzed.")
            self.error.emit("Failure: No files could be analyzed.")

    # --- Specific analysis methods for calf and cow calls ---
    def analyze_calf(self, audio_file_path):
        sound = parselmouth.Sound(audio_file_path)
        duration = sound.get_total_duration()
        if duration <= 0: raise ValueError("Invalid audio duration.")
        
        pitch = call(sound, "To Pitch (cc)", 0, 70, 15, "no", 0.1, 0.2, 0.1, 0.5, 0.1, 110)
        pitch_interp = call(call(pitch, "Smooth", 10), "Interpolate")
        
        f0_mean = call(pitch_interp, "Get mean", 0, 0, "Hertz")
        f0_max = call(pitch_interp, "Get maximum", 0, 0, "Hertz", "Parabolic")
        f0_min = call(pitch_interp, "Get minimum", 0, 0, "Hertz", "Parabolic")
        
        pitch_tier = call(pitch_interp, "Down to PitchTier")
        f0_var, fm_rate, fm_extent = calculate_modulations_fast("pitch", pitch_interp, pitch_tier, duration)
        
        table_voiced = call(pitch_tier, "Down to TableOfReal", "Hertz")
        nrow = call(table_voiced, "Get number of rows")
        f0_start = float(call(table_voiced, "Get value", 1, 2)) if nrow > 0 else np.nan
        f0_end = float(call(table_voiced, "Get value", nrow, 2)) if nrow > 0 else np.nan
        
        q25, q50, q75, fpeak = extract_energy_parameters(sound)
        
        intensity = call(sound, "To Intensity", 70, 0, "yes")
        intensity_tier = call(intensity, "Down to IntensityTier")
        am_var, am_rate, am_extent = calculate_modulations_fast("intensity", intensity, intensity_tier, duration)
        
        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 70, 0.1, 1)
        
        formant = call(sound, "To Formant (burg)", 0, 7, 4300, 0.01, 50)
        table_f = call(call(formant, "Down to FormantTier"), "Down to TableOfReal", "yes", "no")
        
        f_means = [call(table_f, "Get column mean (label)", f"F{i}") for i in range(1, 7)]
        df_sum = sum(f_means[i] - f_means[i-1] for i in range(1, 6))
        df = df_sum / 5
        
        we = calculate_wiener_entropy_faithful(sound, 70, q75, 0.01)
        
        return {
            "Mean F0 (Hz)": f0_mean, "Start F0 (Hz)": f0_start, "End F0 (Hz)": f0_end,
            "Max F0 (Hz)": f0_max, "Min F0 (Hz)": f0_min, "Range F0 (Hz)": f0_max - f0_min,
            "F0 var (Hz/s)": f0_var, "FM Rate (s-1)": fm_rate, "FM Extent (Hz)": fm_extent,
            "Q25% (Hz)": q25, "Q50% (Hz)": q50, "Q75% (Hz)": q75, "Fpeak (Hz)": fpeak,
            "Sound duration (s)": duration, "AM var (dB/s)": am_var, "AM rate (s-1)": am_rate,
            "AM extent (dB)": am_extent, "Harmonicity": call(harmonicity, "Get mean", 0, 0),
            "F1 mean (Hz)": f_means[0], "F2 mean (Hz)": f_means[1], "F3 mean (Hz)": f_means[2],
            "formant dispersal (Hz)": df, "mean wiener entropy": we
        }

    def analyze_cow(self, audio_file_path, call_type="LFC"):
        sound = parselmouth.Sound(audio_file_path)
        duration = sound.get_total_duration()
        if duration <= 0: raise ValueError("Invalid audio duration.")
        
        if call_type == "LFC":
            time_step = 0.01; min_F0 = 60; max_F0 = 120
            max_nb_cand = 15; sil_threshold = 0.15; voic_threshold = 0.15
            oct_cost = 0.1; oct_jump_cost = 0.7; voic_unvoic_cost = 0.14
            time_step_f = 0.01; max_num_formants = 9; max_formant = 4000
            window_length = 0.01; pre_emphasis = 50
        else:
            time_step = 0.01; min_F0 = 60; max_F0 = 300
            max_nb_cand = 15; sil_threshold = 0.15; voic_threshold = 0.15
            oct_cost = 0.1; oct_jump_cost = 0.7; voic_unvoic_cost = 0.14
            time_step_f = 0.01; max_num_formants = 9; max_formant = 3500
            window_length = 0.01; pre_emphasis = 50
            
        pitch = call(sound, "To Pitch (cc)", time_step, min_F0, max_nb_cand, "no", 
                     sil_threshold, voic_threshold, oct_cost, oct_jump_cost, voic_unvoic_cost, max_F0)
        pitch_interp = call(call(pitch, "Smooth", 10), "Interpolate")
        
        f0_mean = call(pitch_interp, "Get mean", 0, 0, "Hertz")
        f0_max = call(pitch_interp, "Get maximum", 0, 0, "Hertz", "Parabolic")
        f0_min = call(pitch_interp, "Get minimum", 0, 0, "Hertz", "Parabolic")
        
        q25, q50, q75, fpeak = extract_energy_parameters(sound)
        
        intensity = call(sound, "To Intensity", min_F0, time_step, "yes")
        intensity_tier = call(intensity, "Down to IntensityTier")
        am_var, am_rate, am_extent = calculate_modulations_fast("intensity", intensity, intensity_tier, duration)
        
        harmonicity = call(sound, "To Harmonicity (cc)", time_step, min_F0, sil_threshold, 1)
        
        formant = call(sound, "To Formant (burg)", time_step_f, max_num_formants, max_formant, window_length, pre_emphasis)
        table_f = call(call(formant, "Down to FormantTier"), "Down to TableOfReal", "yes", "no")
        
        f_means = []
        for i in range(1, 9):
            try: f_means.append(call(table_f, "Get column mean (label)", f"F{i}"))
            except Exception: f_means.append(np.nan)
        
        df_sum = sum(f_means[i] - f_means[i-1] for i in range(1, 7))
        df = df_sum / 7
        
        we = calculate_wiener_entropy_faithful(sound, 50, q75, 0.004)
        
        return {
            "Call type": call_type, "Mean F0": f0_mean, "Max F0": f0_max, 
            "Min F0": f0_min, "Range F0": f0_max - f0_min, "Q25%": q25, "Q50%": q50, 
            "Q75%": q75, "Fpeak": fpeak, "sound duration": duration, 
            "AM var": am_var, "AM rate": am_rate, "AM extent": am_extent, 
            "harmonicity": call(harmonicity, "Get mean", 0, 0), "formant dispersal": df, 
            "mean wiener entropy": we
        }