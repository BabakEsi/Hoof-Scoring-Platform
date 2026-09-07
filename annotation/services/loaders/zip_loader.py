import json
import zipfile

from .base_loader import BaseLoader



class ZipLoader(BaseLoader):

    def load(self):
        self.zip_file = zipfile.ZipFile(self.source)

        self.json_files = [
            name
            for name in self.zip_file.namelist()
            if name.endswith(".json")
        ]

    def __iter__(self):

        for path in self.json_files:
            
            with self.zip_file.open(path) as f:

                content = f.read()          # bytes

                file_hash = self.calculate_hash(content)

                data = json.loads(content)

                yield {
                    "path": path,
                    "data": data,
                    "hash": file_hash,
                }

    def close(self):

        if hasattr(self, "zip_file"):
            self.zip_file.close()