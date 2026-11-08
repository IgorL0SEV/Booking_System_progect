"""Модель бронирования."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    table_id: int
    start_time: datetime
    end_time: datetime
    user_name: str | None = None
    table_number: int | None = None
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "Booking":
        return cls(
            id=row[0],
            user_id=row[1],
            table_id=row[2],
            start_time=row[3],
            end_time=row[4],
            user_name=row[5],
            table_number=row[6],
            created_at=row[7],
        )

    @property
    def period(self) -> str:
        return f"{self.start_time:%d.%m.%Y %H:%M}–{self.end_time:%H:%M}"

    def __str__(self) -> str:
        who = self.user_name or f"user_id={self.user_id}"
        table = (
            f"стол №{self.table_number}"
            if self.table_number is not None
            else f"table_id={self.table_id}"
        )
        return f"#{self.id} {self.period} — {who}, {table}"
