"""
library.py
Core module for a simple Library Management System.
Provides Book, Member, and Library classes with business logic
that can be comprehensively unit-tested.
"""

from datetime import date, timedelta
from typing import Optional


# ──────────────────────────────────────────────
# Custom Exceptions
# ──────────────────────────────────────────────

class BookNotFoundError(Exception):
    """Raised when a book ISBN cannot be located in the catalogue."""

class BookNotAvailableError(Exception):
    """Raised when a book is already checked out."""

class MemberNotFoundError(Exception):
    """Raised when a member ID cannot be located."""

class MemberLimitError(Exception):
    """Raised when a member tries to borrow beyond their allowed limit."""

class InvalidInputError(Exception):
    """Raised for bad/empty input values."""


# ──────────────────────────────────────────────
# Book
# ──────────────────────────────────────────────

class Book:
    """Represents a single book in the library catalogue."""

    def __init__(self, isbn: str, title: str, author: str, copies: int = 1):
        if not isbn or not isbn.strip():
            raise InvalidInputError("ISBN cannot be empty.")
        if not title or not title.strip():
            raise InvalidInputError("Title cannot be empty.")
        if not author or not author.strip():
            raise InvalidInputError("Author cannot be empty.")
        if copies < 0:
            raise InvalidInputError("Copies cannot be negative.")

        self.isbn = isbn.strip()
        self.title = title.strip()
        self.author = author.strip()
        self.total_copies = copies
        self.available_copies = copies

    @property
    def is_available(self) -> bool:
        return self.available_copies > 0

    def checkout(self) -> None:
        """Decrease available copies by 1."""
        if not self.is_available:
            raise BookNotAvailableError(
                f"'{self.title}' has no available copies."
            )
        self.available_copies -= 1

    def return_copy(self) -> None:
        """Increase available copies by 1."""
        if self.available_copies >= self.total_copies:
            raise ValueError("Cannot return more copies than total.")
        self.available_copies += 1

    def __repr__(self) -> str:
        return (
            f"Book(isbn={self.isbn!r}, title={self.title!r}, "
            f"author={self.author!r}, available={self.available_copies}/"
            f"{self.total_copies})"
        )


# ──────────────────────────────────────────────
# Member
# ──────────────────────────────────────────────

BORROW_LIMIT = 3          # max books a member may hold at once
LOAN_DAYS    = 14         # standard loan period in days
FINE_PER_DAY = 0.50       # £0.50 per overdue day


class Member:
    """Represents a registered library member."""

    def __init__(self, member_id: str, name: str):
        if not member_id or not member_id.strip():
            raise InvalidInputError("Member ID cannot be empty.")
        if not name or not name.strip():
            raise InvalidInputError("Member name cannot be empty.")

        self.member_id   = member_id.strip()
        self.name        = name.strip()
        # maps isbn -> due_date
        self._loans: dict[str, date] = {}

    # ── read-only helpers ──────────────────────

    @property
    def loan_count(self) -> int:
        return len(self._loans)

    @property
    def loans(self) -> dict[str, date]:
        return dict(self._loans)   # return a copy

    # ── borrow / return ───────────────────────

    def borrow(self, isbn: str, borrow_date: Optional[date] = None) -> date:
        """
        Record a loan.  Returns the due date.
        Raises MemberLimitError if the member already holds BORROW_LIMIT books.
        Raises ValueError if the member already has this ISBN on loan.
        """
        if self.loan_count >= BORROW_LIMIT:
            raise MemberLimitError(
                f"{self.name} has reached the borrow limit of {BORROW_LIMIT}."
            )
        if isbn in self._loans:
            raise ValueError(f"Member already has ISBN {isbn} on loan.")

        start = borrow_date or date.today()
        due   = start + timedelta(days=LOAN_DAYS)
        self._loans[isbn] = due
        return due

    def return_book(self, isbn: str) -> None:
        """Remove a loan record.  Raises ValueError if ISBN not on loan."""
        if isbn not in self._loans:
            raise ValueError(f"ISBN {isbn} is not currently on loan.")
        del self._loans[isbn]

    # ── fines ─────────────────────────────────

    def calculate_fine(self, isbn: str, return_date: Optional[date] = None) -> float:
        """
        Return the overdue fine for a specific loan.
        Returns 0.0 if the book is returned on time.
        """
        if isbn not in self._loans:
            raise ValueError(f"ISBN {isbn} is not currently on loan.")
        today  = return_date or date.today()
        overdue = (today - self._loans[isbn]).days
        return max(0.0, overdue * FINE_PER_DAY)

    def __repr__(self) -> str:
        return f"Member(id={self.member_id!r}, name={self.name!r}, loans={self.loan_count})"


# ──────────────────────────────────────────────
# Library  (catalogue + member registry)
# ──────────────────────────────────────────────

class Library:
    """
    Top-level façade that coordinates books and members.
    Responsible for checkout / return workflow.
    """

    def __init__(self, name: str = "City Library"):
        self.name    = name
        self._books:   dict[str, Book]   = {}
        self._members: dict[str, Member] = {}

    # ── catalogue management ──────────────────

    def add_book(self, book: Book) -> None:
        if book.isbn in self._books:
            # top up copies instead of rejecting
            existing = self._books[book.isbn]
            existing.total_copies     += book.total_copies
            existing.available_copies += book.total_copies
        else:
            self._books[book.isbn] = book

    def remove_book(self, isbn: str) -> None:
        if isbn not in self._books:
            raise BookNotFoundError(f"ISBN {isbn} not in catalogue.")
        del self._books[isbn]

    def get_book(self, isbn: str) -> Book:
        if isbn not in self._books:
            raise BookNotFoundError(f"ISBN {isbn} not in catalogue.")
        return self._books[isbn]

    def search_by_title(self, query: str) -> list[Book]:
        """Case-insensitive partial-title search."""
        q = query.lower()
        return [b for b in self._books.values() if q in b.title.lower()]

    def search_by_author(self, query: str) -> list[Book]:
        """Case-insensitive partial-author search."""
        q = query.lower()
        return [b for b in self._books.values() if q in b.author.lower()]

    # ── member management ─────────────────────

    def register_member(self, member: Member) -> None:
        if member.member_id in self._members:
            raise ValueError(f"Member ID {member.member_id!r} already registered.")
        self._members[member.member_id] = member

    def get_member(self, member_id: str) -> Member:
        if member_id not in self._members:
            raise MemberNotFoundError(f"Member {member_id!r} not found.")
        return self._members[member_id]

    # ── checkout / return workflow ────────────

    def checkout(
        self,
        member_id: str,
        isbn: str,
        borrow_date: Optional[date] = None,
    ) -> date:
        """
        Check out a book to a member.
        Returns the due date.
        """
        member = self.get_member(member_id)
        book   = self.get_book(isbn)
        book.checkout()                          # raises BookNotAvailableError if needed
        return member.borrow(isbn, borrow_date)  # raises MemberLimitError if needed

    def return_book(
        self,
        member_id: str,
        isbn: str,
        return_date: Optional[date] = None,
    ) -> float:
        """
        Return a book and compute any overdue fine.
        Returns the fine amount (0.0 if on time).
        """
        member = self.get_member(member_id)
        fine   = member.calculate_fine(isbn, return_date)
        member.return_book(isbn)
        self.get_book(isbn).return_copy()
        return fine

    # ── stats ─────────────────────────────────

    def available_books(self) -> list[Book]:
        return [b for b in self._books.values() if b.is_available]

    def catalogue_size(self) -> int:
        return len(self._books)
