"""
tests/test_library.py
=====================
Unit tests for the Library Management System.
Framework : Python stdlib unittest  (pytest-compatible — just run  pytest  or
            python -m unittest discover  — both work with this file)

Run with  : python -m unittest discover -s tests -v
       OR  : pytest tests/test_library.py -v   (if pytest is available)

Each test class covers one logical component.
Every class contains at least 3 test cases:
  • Normal  – typical, expected usage
  • Edge    – boundary / unusual-but-valid input
  • Error   – invalid input that must raise an exception
"""

import unittest
from datetime import date, timedelta
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from library import (
    Book, Member, Library,
    BookNotFoundError, BookNotAvailableError,
    MemberNotFoundError, MemberLimitError, InvalidInputError,
    BORROW_LIMIT, LOAN_DAYS, FINE_PER_DAY,
)


# TEST FUNCTION 1 — Book creation & validation


class TestBookCreation(unittest.TestCase):
    """Tests for Book.__init__ constructor and is_available property."""

    def test_normal_valid_book_attributes(self):
        """
        NORMAL CASE: A Book with valid arguments stores all attributes
        correctly and reports itself as available.
        """
        book = Book(isbn="978-0-06-112008-4",
                    title="To Kill a Mockingbird",
                    author="Harper Lee", copies=3)
        self.assertEqual(book.isbn,             "978-0-06-112008-4")
        self.assertEqual(book.title,            "To Kill a Mockingbird")
        self.assertEqual(book.author,           "Harper Lee")
        self.assertEqual(book.total_copies,     3)
        self.assertEqual(book.available_copies, 3)
        self.assertTrue(book.is_available)

    def test_edge_whitespace_stripped_and_single_copy(self):
        """
        EDGE CASE: Leading/trailing whitespace in isbn/title/author is stripped,
        and a book with exactly 1 copy reports is_available == True.
        """
        book = Book(isbn="  978-1-23-456789-0  ",
                    title="  Dune  ",
                    author="  Frank Herbert  ",
                    copies=1)
        self.assertEqual(book.isbn,   "978-1-23-456789-0")
        self.assertEqual(book.title,  "Dune")
        self.assertEqual(book.author, "Frank Herbert")
        self.assertTrue(book.is_available)

    def test_edge_zero_copies_not_available(self):
        """
        EDGE CASE: A Book created with 0 copies is valid but immediately
        unavailable — important for pre-catalogued not-yet-received stock.
        """
        book = Book(isbn="000", title="Ghost Book", author="Nobody", copies=0)
        self.assertFalse(book.is_available)
        self.assertEqual(book.available_copies, 0)

    def test_error_empty_isbn_raises_invalid_input(self):
        """
        ERROR CASE: An empty or whitespace-only ISBN must raise
        InvalidInputError — the ISBN is the primary key and cannot be blank.
        """
        with self.assertRaises(InvalidInputError):
            Book(isbn="", title="Some Title", author="Some Author")
        with self.assertRaises(InvalidInputError):
            Book(isbn="   ", title="Some Title", author="Some Author")

    def test_error_negative_copies_raises_invalid_input(self):
        """
        ERROR CASE: A negative copy count must raise InvalidInputError —
        inventory cannot physically be negative.
        """
        with self.assertRaises(InvalidInputError):
            Book(isbn="999", title="Bad Book", author="Author", copies=-1)



# TEST FUNCTION 2 — Book checkout & return mechanics


class TestBookCheckoutReturn(unittest.TestCase):
    """Tests for Book.checkout() and Book.return_copy() state transitions."""

    def setUp(self):
        self.book = Book(isbn="ISBN-TWO", title="Twin Tales",
                         author="A.U. Thor", copies=2)

    def test_normal_checkout_decrements_available_copies(self):
        """
        NORMAL CASE: Checking out one copy decrements available_copies
        by exactly 1 while total_copies stays unchanged.
        """
        self.book.checkout()
        self.assertEqual(self.book.available_copies, 1)
        self.assertEqual(self.book.total_copies,     2)
        self.assertTrue(self.book.is_available)

    def test_normal_return_restores_available_copies(self):
        """
        NORMAL CASE: Returning a copy after a checkout restores
        available_copies to its original value.
        """
        self.book.checkout()
        self.book.return_copy()
        self.assertEqual(self.book.available_copies, 2)
        self.assertTrue(self.book.is_available)

    def test_edge_checkout_last_copy_makes_book_unavailable(self):
        """
        EDGE CASE: After checking out ALL copies the book must report
        is_available == False and available_copies == 0.
        """
        self.book.checkout()
        self.book.checkout()
        self.assertFalse(self.book.is_available)
        self.assertEqual(self.book.available_copies, 0)

    def test_error_checkout_when_none_available_raises(self):
        """
        ERROR CASE: A third checkout attempt when only 2 copies exist
        must raise BookNotAvailableError.
        """
        self.book.checkout()
        self.book.checkout()
        with self.assertRaises(BookNotAvailableError):
            self.book.checkout()

    def test_error_return_excess_raises_value_error(self):
        """
        ERROR CASE: Returning a copy when available_copies already equals
        total_copies must raise ValueError — no phantom returns allowed.
        """
        with self.assertRaises(ValueError):
            self.book.return_copy()



# TEST FUNCTION 3 — Member borrowing & loan tracking


class TestMemberBorrowing(unittest.TestCase):
    """Tests for Member.borrow() and Member.return_book()."""

    def setUp(self):
        self.member = Member(member_id="M001", name="Ayesha Khan")

    def test_normal_borrow_records_loan_and_returns_due_date(self):
        """
        NORMAL CASE: Borrowing a book records it in the member's loans
        and returns a due date exactly LOAN_DAYS from the borrow date.
        """
        borrow_date = date(2025, 1, 1)
        due = self.member.borrow("ISBN-001", borrow_date)
        self.assertEqual(due, borrow_date + timedelta(days=LOAN_DAYS))
        self.assertIn("ISBN-001", self.member.loans)
        self.assertEqual(self.member.loan_count, 1)

    def test_edge_borrow_up_to_the_exact_limit(self):
        """
        EDGE CASE: A member can borrow exactly BORROW_LIMIT books without
        an error; loan_count must equal BORROW_LIMIT afterwards.
        """
        for i in range(BORROW_LIMIT):
            self.member.borrow(f"ISBN-{i:03d}")
        self.assertEqual(self.member.loan_count, BORROW_LIMIT)

    def test_error_borrow_beyond_limit_raises_member_limit_error(self):
        """
        ERROR CASE: A (BORROW_LIMIT + 1)-th borrow must raise
        MemberLimitError — the member has hit their cap.
        """
        for i in range(BORROW_LIMIT):
            self.member.borrow(f"ISBN-{i:03d}")
        with self.assertRaises(MemberLimitError):
            self.member.borrow("ISBN-EXTRA")

    def test_error_duplicate_isbn_borrow_raises_value_error(self):
        """
        ERROR CASE: Borrowing the same ISBN twice without returning it
        must raise ValueError — a member can't hold two copies of the
        same title simultaneously.
        """
        self.member.borrow("ISBN-DUP")
        with self.assertRaises(ValueError):
            self.member.borrow("ISBN-DUP")

    def test_normal_return_removes_loan_record(self):
        """
        NORMAL CASE: Returning a borrowed book removes it from the loans
        dict and reduces loan_count by 1.
        """
        self.member.borrow("ISBN-RET")
        self.member.return_book("ISBN-RET")
        self.assertNotIn("ISBN-RET", self.member.loans)
        self.assertEqual(self.member.loan_count, 0)

    def test_error_return_unborrowed_isbn_raises_value_error(self):
        """
        ERROR CASE: Returning an ISBN that was never borrowed must raise
        ValueError — prevents phantom returns from corrupting the count.
        """
        with self.assertRaises(ValueError):
            self.member.return_book("ISBN-NEVER")



# TEST FUNCTION 4 — Overdue fine calculation


class TestFineCalculation(unittest.TestCase):
    """Tests for Member.calculate_fine()."""

    def setUp(self):
        self.member      = Member(member_id="M002", name="Ibrahim Malik")
        self.borrow_date = date(2025, 1, 1)
        self.member.borrow("ISBN-FINE", self.borrow_date)
        self.due_date = self.borrow_date + timedelta(days=LOAN_DAYS)

    def test_normal_no_fine_when_returned_on_due_date(self):
        """
        NORMAL CASE: Returning the book exactly on the due date yields
        a fine of 0.0 — on-time is never penalised.
        """
        fine = self.member.calculate_fine("ISBN-FINE", return_date=self.due_date)
        self.assertEqual(fine, 0.0)

    def test_normal_correct_fine_for_overdue_days(self):
        """
        NORMAL CASE: Returning 5 days after the due date incurs a fine
        of exactly 5 × FINE_PER_DAY.
        """
        late = self.due_date + timedelta(days=5)
        fine = self.member.calculate_fine("ISBN-FINE", return_date=late)
        self.assertAlmostEqual(fine, 5 * FINE_PER_DAY)

    def test_edge_early_return_yields_zero_fine(self):
        """
        EDGE CASE: Returning one day before the due date must yield 0.0
        — negative overdue days are clamped to zero, never a reward.
        """
        early = self.due_date - timedelta(days=1)
        fine  = self.member.calculate_fine("ISBN-FINE", return_date=early)
        self.assertEqual(fine, 0.0)

    def test_error_fine_for_unknown_isbn_raises_value_error(self):
        """
        ERROR CASE: Calling calculate_fine for an ISBN not on loan
        must raise ValueError.
        """
        with self.assertRaises(ValueError):
            self.member.calculate_fine("ISBN-NOTLOANED", return_date=date(2025, 2, 1))



# TEST FUNCTION 5 — Library catalogue search


class TestLibrarySearch(unittest.TestCase):
    """Tests for Library.search_by_title() and Library.search_by_author()."""

    def setUp(self):
        self.lib = Library("Test Library")
        self.lib.add_book(Book("ISBN-A", "The Great Gatsby",      "F. Scott Fitzgerald", 2))
        self.lib.add_book(Book("ISBN-B", "Great Expectations",    "Charles Dickens",     1))
        self.lib.add_book(Book("ISBN-C", "Pride and Prejudice",   "Jane Austen",         3))
        self.lib.add_book(Book("ISBN-D", "Sense and Sensibility", "Jane Austen",         1))
        self.lib.add_book(Book("ISBN-E", "Oliver Twist",          "Charles Dickens",     2))

    def test_normal_title_search_returns_matching_books(self):
        """
        NORMAL CASE: Searching 'great' returns exactly the two books
        whose titles contain that substring.
        """
        results = self.lib.search_by_title("great")
        titles  = {b.title for b in results}
        self.assertIn("The Great Gatsby",   titles)
        self.assertIn("Great Expectations", titles)
        self.assertEqual(len(results), 2)

    def test_normal_author_search_returns_all_books_by_author(self):
        """
        NORMAL CASE: Searching 'Jane Austen' returns both her books.
        """
        results = self.lib.search_by_author("Jane Austen")
        titles  = {b.title for b in results}
        self.assertIn("Pride and Prejudice",   titles)
        self.assertIn("Sense and Sensibility", titles)
        self.assertEqual(len(results), 2)

    def test_edge_search_is_case_insensitive(self):
        """
        EDGE CASE: UPPER, lower, and Mixed-case queries all return the
        same results — search must be fully case-insensitive.
        """
        upper  = self.lib.search_by_author("DICKENS")
        lower  = self.lib.search_by_author("dickens")
        proper = self.lib.search_by_author("Dickens")
        self.assertEqual(len(upper), 2)
        self.assertEqual(len(lower), 2)
        self.assertEqual(len(proper), 2)

    def test_edge_partial_title_match(self):
        """
        EDGE CASE: The short substring 'and' matches 'Pride and Prejudice'
        and 'Sense and Sensibility' — partial matching must work.
        """
        results = self.lib.search_by_title("and")
        self.assertEqual(len(results), 2)

    def test_error_no_match_returns_empty_list(self):
        """
        ERROR CASE: A query matching no book returns [] instead of
        raising an exception — safe to iterate.
        """
        self.assertEqual(self.lib.search_by_title("Zzz No Such Book"), [])
        self.assertEqual(self.lib.search_by_author("Nobody Author"),   [])



# TEST FUNCTION 6 — End-to-end checkout / return workflow


class TestLibraryCheckoutReturnWorkflow(unittest.TestCase):
    """
    Integration-style unit tests for Library.checkout() and
    Library.return_book() — verifies the full borrowing lifecycle.
    """

    def setUp(self):
        self.lib = Library("Workflow Library")
        self.lib.add_book(Book("ISBN-WF", "Workflow Book", "Test Author", copies=1))
        self.lib.register_member(Member("M-WF", "Test Member"))
        self.borrow_date = date(2025, 3, 1)

    def test_normal_checkout_and_on_time_return_no_fine(self):
        """
        NORMAL CASE: Member checks out the book and returns it on the
        due date — fine is 0.0 and the book becomes available again.
        """
        due  = self.lib.checkout("M-WF", "ISBN-WF", self.borrow_date)
        fine = self.lib.return_book("M-WF", "ISBN-WF", return_date=due)
        self.assertEqual(fine, 0.0)
        self.assertTrue(self.lib.get_book("ISBN-WF").is_available)

    def test_normal_late_return_incurs_correct_fine(self):
        """
        NORMAL CASE: Returning the book 3 days late produces a fine of
        exactly 3 × FINE_PER_DAY.
        """
        due         = self.lib.checkout("M-WF", "ISBN-WF", self.borrow_date)
        late_return = due + timedelta(days=3)
        fine        = self.lib.return_book("M-WF", "ISBN-WF", return_date=late_return)
        self.assertAlmostEqual(fine, 3 * FINE_PER_DAY)

    def test_edge_checkout_removes_book_from_available_list(self):
        """
        EDGE CASE: After the only copy is checked out, the book must not
        appear in Library.available_books().
        """
        self.lib.checkout("M-WF", "ISBN-WF", self.borrow_date)
        available_isbns = {b.isbn for b in self.lib.available_books()}
        self.assertNotIn("ISBN-WF", available_isbns)

    def test_error_checkout_unknown_member_raises_member_not_found(self):
        """
        ERROR CASE: Using a non-existent member ID must raise
        MemberNotFoundError immediately.
        """
        with self.assertRaises(MemberNotFoundError):
            self.lib.checkout("GHOST", "ISBN-WF", self.borrow_date)

    def test_error_checkout_unavailable_book_does_not_record_loan(self):
        """
        ERROR CASE: Checking out a book with no copies left must raise
        BookNotAvailableError AND must not record any loan on the member.
        """
        self.lib.checkout("M-WF", "ISBN-WF", self.borrow_date)
        self.lib.register_member(Member("M-WF2", "Second Member"))
        with self.assertRaises(BookNotAvailableError):
            self.lib.checkout("M-WF2", "ISBN-WF", self.borrow_date)
        second = self.lib.get_member("M-WF2")
        self.assertEqual(second.loan_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
