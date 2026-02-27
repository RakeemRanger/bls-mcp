import json
from pathlib import Path
from typing import Dict, Any

class JsonUtility:
    """Utility for reading and writing JSON files."""
    
    def __init__(self, json_path: str | Path):
        self.file_path = Path(json_path).resolve()
    
    def load(self) -> Dict[str, Any]:
        """Load and parse JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON file not found: {self.file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.file_path}: {e}")
    
    def save(self, data: Dict[str, Any], indent: int = 2) -> None:
        """Write data to JSON file."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def load_from(path: str | Path) -> Dict[str, Any]:
        """Quick load without instantiation."""
        with open(Path(path).resolve(), 'r', encoding='utf-8') as f:
            return json.load(f)