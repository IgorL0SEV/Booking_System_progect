"""Модель стола."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    id: int
    number: int
    seats: int
    location: str | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "Table":
        return cls(id=row[0], number=row[1], seats=row[2], location=row[3])

    def __str__(self) -> str:
        place = f", {self.location}" if self.location else ""
        return f"#{self.id} Стол №{self.number}, мест: {self.seats}{place}"
