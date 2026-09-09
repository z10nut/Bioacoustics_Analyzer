import os

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QProgressBar
from PyQt6.QtGui import QFont

class ActionPanelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.models_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(self.models_dir, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.label_actions = QLabel("Actions:")
        self.label_actions.setFont(QFont("Arial", 12))
        layout.addWidget(self.label_actions)

        self.model_selector = QComboBox()
        self.model_selector.setFont(QFont("Arial", 11))
        self.model_selector.setMinimumHeight(35)
        self.add_models()
        layout.addWidget(self.model_selector)

        layout.addSpacing(10)

        self.btn_view_edit = QPushButton("View/Edit Waveform")
        layout.addWidget(self.btn_view_edit)
        self.btn_run_analysis = QPushButton("Run Analysis")
        layout.addWidget(self.btn_run_analysis)
        self.btn_manual_labeling = QPushButton("Manual Labeling")
        layout.addWidget(self.btn_manual_labeling)

        for btn in [self.btn_view_edit, self.btn_run_analysis, self.btn_manual_labeling]:
            btn.setFont(QFont("Arial", 11))
            btn.setMinimumHeight(40)
            layout.addWidget(btn)

        # Progress bar
        layout.addSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def add_models(self):
        self.model_selector.clear()
        try:
            models = [f for f in os.listdir(self.models_dir) if os.path.isfile(os.path.join(self.models_dir, f))]
            if models:
                self.model_selector.addItems(models)
            else:
                self.model_selector.addItem("No models available")
        except Exception:
            self.model_selector.addItem("Error loading models")

    def get_selected_model(self):
        """Returns the currently selected model from the dropdown."""
        return self.model_selector.currentText()