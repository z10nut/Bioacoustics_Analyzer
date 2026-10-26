import os
import shutil
import re
import logging

logger = logging.getLogger(__name__)

class QCActionManager:
    def __init__(self, base_dir):
        """Initialize the QCActionManager with a base directory."""
        self.base_dir = base_dir
        self.hfc_dir = os.path.join(base_dir, 'HFC')
        self.lfc_dir = os.path.join(base_dir, 'LFC')
        self.noise_dir = os.path.join(base_dir, 'Noise')

        for d in [self.hfc_dir, self.lfc_dir, self.noise_dir]:
            os.makedirs(d, exist_ok=True)

        self.undo_stack = []
        self.redo_stack = []
        logger.info("QCActionManager initialized with base directory: %s", base_dir)

    def _get_next_filename(self, target_dir, prefix):
        """Finds the next available ID and returns the new valid filename."""
        max_id = 0
        pattern = re.compile(rf"{prefix}_(\d+)\.wav", re.IGNORECASE)

        for filename in os.listdir(target_dir):
            match = pattern.match(filename)
            if match:
                idx = int(match.group(1))
                max_id = max(max_id, idx)

        new_file = os.path.join(target_dir, f"{prefix}_{max_id + 1}.wav")
        return new_file

    def classify_file(self, current_filepath, label):
        """Classifies the file into the specified label directory and returns the new filepath."""
        if not os.path.exists(current_filepath):
            logger.error("Current file does not exist: %s", current_filepath)
            return None

        if label == 'HFC':
            new_filepath = self._get_next_filename(self.hfc_dir, 'HFC')
        elif label == 'LFC':
            new_filepath = self._get_next_filename(self.lfc_dir, 'LFC')
        elif label == 'Noise':
            new_filepath = self._get_next_filename(self.noise_dir, 'Noise')
        else:
            logger.error("Invalid label provided: %s", label)
            return None
        try:
            shutil.move(current_filepath, new_filepath)
            logger.info(f"Classified '{os.path.basename(current_filepath)}' as {label} -> '{os.path.basename(new_filepath)}'")

            action = {
                'src': current_filepath,
                'dst': new_filepath,
                'label': label
            }
            self.undo_stack.append(action)
            self.redo_stack.clear()
            return new_filepath
        
        except Exception as e:
            logger.error(f"Failed to move file during classification: {e}")
            return None

    def undo(self):
        if not self.undo_stack:
            logger.debug("Undo stack is empty. Nothing to undo.")
            return None
        
        action = self.undo_stack.pop()

        if os.path.exists(action['dst']):
            try:
                shutil.move(action['dst'], action['src'])
                self.redo_stack.append(action)
                logger.info(f"Undo action: Restored '{os.path.basename(action['dst'])}' back to '{os.path.basename(action['src'])}'")
                return action['src']
            except Exception as e:
                logger.error(f"Failed to Undo action: {e}")
        else:
            logger.warning(f"Destination file for undo does not exist: {action['dst']}")

        return None

    def redo(self):
        if not self.redo_stack:
            logger.debug("Redo stack is empty. Nothing to redo.")
            return None
        
        action = self.redo_stack.pop()

        if os.path.exists(action['src']):
            try:
                shutil.move(action['src'], action['dst'])
                self.undo_stack.append(action)
                logger.info(f"Redo action: Moved '{os.path.basename(action['src'])}' back to '{os.path.basename(action['dst'])}'")
                return action['dst']
            except Exception as e:
                logger.error(f"Failed to Redo action: {e}")
        else:
            logger.warning(f"Source file for redo does not exist: {action['src']}")

        return None