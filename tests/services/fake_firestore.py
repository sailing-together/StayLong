"""Minimal in-memory Firestore-shaped client for repository adapter tests."""


class AlreadyExists(Exception):
    """Match the duplicate-document outcome used by Firestore's create API."""


class FakeSnapshot:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, object]:
        return self._data.copy()


class FakeDocument:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}
        self._data: dict[str, object] | None = None

    def collection(self, name: str) -> "FakeCollection":
        return self._collections.setdefault(name, FakeCollection())

    def set(self, data: dict[str, object]) -> None:
        self._data = data.copy()

    def create(self, data: dict[str, object]) -> None:
        if self._data is not None:
            raise AlreadyExists()
        self._data = data.copy()


class FakeCollection:
    def __init__(self) -> None:
        self._documents: dict[str, FakeDocument] = {}

    def document(self, identifier: str) -> FakeDocument:
        return self._documents.setdefault(identifier, FakeDocument())

    def stream(self) -> tuple[FakeSnapshot, ...]:
        return tuple(
            FakeSnapshot(document._data)
            for document in self._documents.values()
            if document._data is not None
        )

    def where(self, field_path: str, op_string: str, value: object) -> "FakeQuery":
        assert op_string == "=="
        return FakeQuery(self, field_path, value)


class FakeQuery:
    def __init__(self, collection: FakeCollection, field_path: str, value: object) -> None:
        self._collection = collection
        self._field_path = field_path
        self._value = value

    def stream(self) -> tuple[FakeSnapshot, ...]:
        return tuple(
            snapshot
            for snapshot in self._collection.stream()
            if snapshot.to_dict()[self._field_path] == self._value
        )


class FakeFirestoreClient:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def collection(self, name: str) -> FakeCollection:
        return self._collections.setdefault(name, FakeCollection())
