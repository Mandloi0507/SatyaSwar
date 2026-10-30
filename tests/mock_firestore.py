"""
SatyaSwar - Mock Firestore In-Memory Engine for Automated Testing
Member 2: Backend, Infrastructure, Database and Security

Provides an in-memory emulation of Cloud Firestore collections, documents,
queries, and mutations to enable fast, offline, deterministic unit testing.
"""

import uuid
from copy import deepcopy
from typing import Any, Dict, Iterator, List, Optional


class MockDocumentSnapshot:
    """Emulates a Firestore DocumentSnapshot."""

    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = deepcopy(data) if data is not None else None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return deepcopy(self._data)

    def get(self, field: str, default: Any = None) -> Any:
        if self._data and field in self._data:
            return self._data[field]
        return default


class MockDocumentReference:
    """Emulates a Firestore DocumentReference."""

    def __init__(self, collection: "MockCollectionReference", doc_id: str):
        self.collection = collection
        self.id = doc_id

    def get(self, transaction: Any = None) -> MockDocumentSnapshot:
        data = self.collection.store.get(self.id)
        return MockDocumentSnapshot(self.id, data)

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        if merge and self.id in self.collection.store:
            self.collection.store[self.id].update(deepcopy(data))
        else:
            self.collection.store[self.id] = deepcopy(data)

    def update(self, data: Dict[str, Any]) -> None:
        if self.id not in self.collection.store:
            raise KeyError(f"Document {self.id} does not exist")
        self.collection.store[self.id].update(deepcopy(data))

    def delete(self) -> None:
        self.collection.store.pop(self.id, None)


class MockQuery:
    """Emulates a Firestore Query with chained filters, ordering, and limits."""

    def __init__(self, collection: "MockCollectionReference"):
        self.collection = collection
        self.filters: List[tuple[str, str, Any]] = []
        self._order_by: Optional[tuple[str, Any]] = None
        self._limit: Optional[int] = None

    def where(self, field: str, op: str, value: Any) -> "MockQuery":
        new_q = MockQuery(self.collection)
        new_q.filters = list(self.filters)
        new_q.filters.append((field, op, value))
        new_q._order_by = self._order_by
        new_q._limit = self._limit
        return new_q

    def order_by(self, field: str, direction: Any = None) -> "MockQuery":
        new_q = MockQuery(self.collection)
        new_q.filters = list(self.filters)
        new_q._order_by = (field, direction)
        new_q._limit = self._limit
        return new_q

    def limit(self, count: int) -> "MockQuery":
        new_q = MockQuery(self.collection)
        new_q.filters = list(self.filters)
        new_q._order_by = self._order_by
        new_q._limit = count
        return new_q

    def stream(self) -> Iterator[MockDocumentSnapshot]:
        results = []
        for doc_id, doc_data in self.collection.store.items():
            matches = True
            for field, op, value in self.filters:
                actual = doc_data.get(field)
                if op in ("==", "eq"):
                    if actual != value:
                        matches = False
                        break
                elif op in ("!=", "ne"):
                    if actual == value:
                        matches = False
                        break
                elif op == ">":
                    if not (actual is not None and actual > value):
                        matches = False
                        break
                elif op == "<":
                    if not (actual is not None and actual < value):
                        matches = False
                        break
                elif op == ">=":
                    if not (actual is not None and actual >= value):
                        matches = False
                        break
                elif op == "<=":
                    if not (actual is not None and actual <= value):
                        matches = False
                        break
            if matches:
                # Include a reference back so doc.reference.update/delete work
                snap = MockDocumentSnapshot(doc_id, doc_data)
                snap.reference = MockDocumentReference(self.collection, doc_id)
                results.append(snap)

        if self._order_by:
            field, direction = self._order_by
            reverse = str(direction).lower() in ("descending", "desc")
            results.sort(
                key=lambda s: (s.get(field) is not None, s.get(field)),
                reverse=reverse,
            )

        if self._limit is not None:
            results = results[: self._limit]

        return iter(results)


class MockCollectionReference:
    """Emulates a Firestore CollectionReference."""

    def __init__(self, name: str):
        self.name = name
        self.store: Dict[str, Dict[str, Any]] = {}

    def document(self, doc_id: Optional[str] = None) -> MockDocumentReference:
        if not doc_id:
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        return MockDocumentReference(self, doc_id)

    def where(self, field: str, op: str, value: Any) -> MockQuery:
        return MockQuery(self).where(field, op, value)

    def order_by(self, field: str, direction: Any = None) -> MockQuery:
        return MockQuery(self).order_by(field, direction)

    def limit(self, count: int) -> MockQuery:
        return MockQuery(self).limit(count)

    def stream(self) -> Iterator[MockDocumentSnapshot]:
        return MockQuery(self).stream()


class MockFirestoreClient:
    """Top-level Firestore Client emulator storing all collections in-memory."""

    def __init__(self):
        self.collections: Dict[str, MockCollectionReference] = {}

    def collection(self, name: str) -> MockCollectionReference:
        if name not in self.collections:
            self.collections[name] = MockCollectionReference(name)
        return self.collections[name]
