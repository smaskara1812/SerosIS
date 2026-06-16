import pickle
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from langchain_core.documents import Document
from langchain_core.stores import BaseStore


class PickleDocStore(BaseStore[str, Document]):
    """Simple file-backed document store.

    Persists parent documents to a single pickle file so the vectorstore
    and docstore stay in sync across server restarts without needing an
    external database.
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Document] = {}
        if self._path.exists():
            with open(self._path, "rb") as f:
                self._data = pickle.load(f)

    def _save(self) -> None:
        with open(self._path, "wb") as f:
            pickle.dump(self._data, f)

    def mget(self, keys: Sequence[str]) -> List[Optional[Document]]:
        return [self._data.get(k) for k in keys]

    def mset(self, key_value_pairs: Sequence[Tuple[str, Document]]) -> None:
        for k, v in key_value_pairs:
            self._data[k] = v
        self._save()

    def mdelete(self, keys: Sequence[str]) -> None:
        for k in keys:
            self._data.pop(k, None)
        self._save()

    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        for k in self._data:
            if prefix is None or k.startswith(prefix):
                yield k

    def clear(self) -> None:
        self._data = {}
        self._save()
