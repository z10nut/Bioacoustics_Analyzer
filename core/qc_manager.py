import os
import shutil
import re

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

    def _get_next_filename(self, target_dir, prefix):
        """Finds the next available ID and returns the new valid filename."""
        max_id = 0
        pattern = re.compile(rf"{prefix}_(\d+)\.wav", re.IGNORECASE)

        for filename in os.listdir(target_dir):
            match = pattern.match(filename)
            if match:
                idx = int(match.group(1))
                max_id = max(max_id, idx)

        return os.path.join(target_dir, f"{prefix}_{max_id + 1}.wav")

    def classify_file(self, current_filepath, label):

        if not os.path.exists(current_filepath):
            return None

        if label == 'HFC':
            new_filepath = self._get_next_filename(self.hfc_dir, 'HFC')
        elif label == 'LFC':
            new_filepath = self._get_next_filename(self.lfc_dir, 'LFC')
        elif label == 'Noise':
            new_filepath = self._get_next_filename(self.noise_dir, 'Noise')
        else:
            return None

        shutil.move(current_filepath, new_filepath)

        action = {
            'src': current_filepath,
            'dst': new_filepath,
            'label': label
        }
        self.undo_stack.append(action)
        self.redo_stack.clear()

        return new_filepath

    def undo(self):
        if not self.undo_stack:
            return None
        
        action = self.undo_stack.pop()

        if os.path.exists(action['dst']):
            shutil.move(action['dst'], action['src'])
            self.redo_stack.append(action)
            return action['src']

        return None

    def redo(self):
        if not self.redo_stack:
            return None
        
        action = self.redo_stack.pop()

        if os.path.exists(action['src']):
            shutil.move(action['src'], action['dst'])
            self.undo_stack.append(action)
            return action['dst']

        return None