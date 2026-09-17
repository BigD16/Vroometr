from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ScanResult:
    status: Literal["not_scanned", "clean", "infected"]
    scanner_version: str


    def __post_init__(self) -> None:
        if self.status not in {"not_scanned", "clean", "infected"}:
            raise ValueError("invalid scan outcome")
        if not self.scanner_version or len(self.scanner_version) > 128:
            raise ValueError("invalid scanner version")


class MalwareScanner(Protocol):
    def scan(self, object_key: str) -> ScanResult: ...


class UnconfiguredScanner:
    def scan(self, object_key: str) -> ScanResult:
        return ScanResult("not_scanned", "unconfigured")
