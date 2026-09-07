from pathlib import Path
import json
import hashlib


class DirectoryLoader:

    def __init__(self, dataset_path):
        self.dataset_path = Path(dataset_path)
        self.items = []

    def load(self):
        self.items = []

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Directory does not exist: {self.dataset_path}"
            )

        for path in self.dataset_path.rglob("*.json"):

            with open(path, "rb") as f:
                raw = f.read()

            self.items.append({
                "path": path.as_posix(),
                "hash": hashlib.sha256(raw).hexdigest(),
                "data": json.loads(raw.decode("utf-8")),
            })

    def __iter__(self):
        return iter(self.items)

    def close(self):
        pass