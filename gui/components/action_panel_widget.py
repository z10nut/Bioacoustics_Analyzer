import os
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QProgressBar
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

class ActionPanelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.models_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(self.models_dir, exist_ok=True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label_actions = QLabel("Actions:")
        self.label_actions.setFont(QFont("Arial", 12))
        layout.addWidget(self.label_actions)

        model_layout = QHBoxLayout()
        self.model_selector = QComboBox()
        self.model_selector.setFont(QFont("Arial", 11))
        self.model_selector.setMinimumHeight(35)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setFixedSize(35, 35)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setToolTip("Refresh models list")
        self.btn_refresh.clicked.connect(self.refresh_models)

        model_layout.addWidget(self.model_selector, stretch=1)
        model_layout.addWidget(self.btn_refresh)
        layout.addLayout(model_layout)

        self.refresh_models()  # Load models on initialization
        layout.addSpacing(10)

        # Actions buttons
        self.btn_view_edit = QPushButton("View/Edit Waveform")
        self.btn_run_analysis = QPushButton("Run Analysis")
        self.btn_manual_labeling = QPushButton("Manual Labeling")

        for btn in [self.btn_view_edit, self.btn_run_analysis, self.btn_manual_labeling]:
            btn.setFont(QFont("Arial", 11))
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

        layout.addSpacing(10)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addStretch()  

    def refresh_models(self):
        """Refresh the list of models in the dropdown."""
        self.model_selector.clear()
        valid_extenstions = ('.pkl', '.h5', '.py')
        try:
            models = [
                f for f in os.listdir(self.models_dir)
                if os.path.isfile(os.path.join(self.models_dir, f)) and f.lower().endswith(valid_extenstions)
            ]
            if models:
                self.model_selector.addItems(models)
                logger.info(f"Models refreshed: {models}")
            else:
                self.model_selector.addItem("No models found")
                logger.warning("No models found in the models directory.")
        except Exception:
            self.model_selector.addItem("Error loading models")
            logger.error("Error occurred while loading models.")

    def get_selected_model(self):
        """Returns the currently selected model from the dropdown."""
        text = self.model_selector.currentText()
        if text in ["No models found", "Error loading models"]:
            logger.warning("No valid model selected.")
            return None

        logger.info(f"Selected model: {text}")
        return text