from abc import ABC, abstractmethod
import hashlib


class BaseLoader(ABC):

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def load(self):
        """
        Prepare data source.
        Called once before iterating.
        """
        pass

    @abstractmethod
    def __iter__(self):
        """
        Iterate over json files.

        Must yield dictionaries like:

        {
            "path": "...",
            "data": {...}
        }
        """
        pass

    @abstractmethod
    def close(self):
        """
        Cleanup resources if needed.
        """
        pass
    
    @property
    def name(self):
        return self.__class__.__name__
    
    @staticmethod
    def calculate_hash(content: bytes):
        return hashlib.sha256(content).hexdigest()