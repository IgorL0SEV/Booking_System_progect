"""Модель пользователя."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    name: str
    phone: str
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "User":
        return cls(id=row[0], name=row[1], phone=row[2], created_at=row[3])

    def __str__(self) -> str:
        return f"#{self.id} {self.name} — {self.phone}"
