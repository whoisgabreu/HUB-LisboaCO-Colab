import json
import os
from typing import List, Dict, Any, Optional

DATA_DIR = "backend/data"

class JSONStore:
    def __init__(self, collection_name: str):
        self.file_path = os.path.join(DATA_DIR, f"{collection_name}.json")
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8-sig") as f:
                json.dump([], f, ensure_ascii=False)

    def _read(self) -> List[Dict[str, Any]]:
        with open(self.file_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def _write(self, data: List[Dict[str, Any]]):
        with open(self.file_path, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    def find_all(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        data = self._read()
        if not query:
            return data
        return [
            item for item in data 
            if all(item.get(k) == v for k, v in query.items())
        ]

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        items = self.find_all(query)
        return items[0] if items else None

    def insert(self, item: Dict[str, Any]):
        data = self._read()
        data.append(item)
        self._write(data)
        return item

    def update(self, query: Dict[str, Any], update_data: Dict[str, Any]):
        data = self._read()
        updated = False
        for item in data:
            if all(item.get(k) == v for k, v in query.items()):
                item.update(update_data)
                updated = True
        if updated:
            self._write(data)
        return updated

    def delete(self, query: Dict[str, Any]):
        data = self._read()
        new_data = [
            item for item in data 
            if not all(item.get(k) == v for k, v in query.items())
        ]
        if len(new_data) < len(data):
            self._write(new_data)
            return True
        return False
