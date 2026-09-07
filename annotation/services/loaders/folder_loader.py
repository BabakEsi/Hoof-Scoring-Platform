import json
from pathlib import Path

from .base_loader import BaseLoader


class FolderLoader(BaseLoader):

    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)
        self.json_items = []

    def load(self):

        if not self.folder_path.exists():
            raise FileNotFoundError(self.folder_path)

        self.json_items = sorted(
            self.folder_path.rglob("*.json")
        )

    def __iter__(self):

        for json_file in self.json_items:

            content = json_file.read_bytes()

            yield {
                "path": str(json_file),
                "data": json.loads(content),
                "hash": self.calculate_hash(content),
            }

    def close(self):
        pass