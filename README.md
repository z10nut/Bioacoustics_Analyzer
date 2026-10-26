# Bioacoustics Analyzer

An open-source, cross-platform desktop application build with Python and PyQt6 for the automated detection, manual quality control and precise annotations of animal vocalizations.

Originally developed for compiling bovine acoustic datasets (e.g. differentiating between High-Frequency Calls and Low-Frequency Calls), the tool features a plug and play architecture that allows researchers to integrate any custom learning model for specific bioacoustics research.

## Key Features

* **Automated Detection Pipeline:** Run sliding-window inference using pre-trained models to isolate animal vocalizations from long field recordings.
* **Rapid Manual QC Tool:** A high-speed, hotkey-driven interface for researchers to quickly validate and categorize AI-generated detections into classes (e.g., HFC, LFC, Noise).
* **Precision waveform & Spectrogram Viewer:** A detailed, Praat-style interactive viewer to manually adjust annotation boundaries, visualize high-resolution spectrograms and export data.
* **Cross-Platform CI/CD:** Standalone executables available for Windows, macOS and Linux, requiring no Python installation for end-users.
* **Custom Model Plugin API:** Easily inject your own PyTorch, TensorFlow or Scikit-Learn models without altering the core GUI application.

## Workflows

### 1. Automated Detection
    1. Load a raw *.wav* recording.
    2. Select your acoustic model from the dropdown.
    3. Click *Run Analysis*. The engine will extract audio chunks where vocalizations are detected and save them into a centralized **Detections/** folder, alognside an Excel report containing timestamps.

### 2. Precision Annotation

For fine-tuning annotation boundaries:
 * Use the **Load Model Output** button to import the AI generated *.xlsx* or *.csv* files.
 * Click and drag the yellow boundaries to adjust *tmin* and *tmax*.
 * Double-click a label to rename it.
 * Press **Save Labels** to export the cleaned dataset as a *.json*, *.csv* or *.xlsx* file.

### 3. Manual Quality Control

Use the **Manual Labeling** tab to rapidly validate the raw detections. The tool auto-plays the isolated audio chunk (with contextual padding) and displays a synchronized waveform and spectrogram.

|              Hotkey| Action                                            |
|--------------------|---------------------------------------------------|
|                   1| Categorize as LFC (Move file to LFC directory)
|                   2| Categorize as HFC (Move file to HFC directory)
|                   3| Categorize as Noise (Trashes the false positive)
|               Space| Play the current audio segmenet
|     Ctrl+Z / Ctrl+Y| Undo / Redo last categorization

## Contributing

Contributions, issues and feature reuqests are welcome!  
Feel free to check issues page.