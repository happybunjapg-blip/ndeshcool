"""Regression tests for the Business Day gate fix.

Bug: a Business Day belongs to the *business*, not to an individual user.
When a co-owner had already opened one, a worker landing on the gate and
clicking "Open Business Day" caused BusinessDayService.open_day() to
attempt an INSERT of a second OPEN row, which the database's
one_open_business_day_per_business unique constraint correctly rejected --
surfacing as an unhandled duplicate-key error instead of just letting the
worker proceed with the business's existing open day.

Fix: BusinessDayService.open_day() now always checks the authoritative
server state first (AppState.sync_open_business_day(), which calls
Repository.get_open_business_day() -- not the possibly-stale local cache)
and reuses that day when one exists. A new day is only created when the
authoritative check confirms none is open. A narrow safety net remains for
the genuine race where two clients both pass that check at nearly the same
instant: DuplicateBusinessDayError (raised by the repository when the DB
constraint fires) is caught and resolved by re-fetching the day that won,
rather than surfacing an error.

These tests exercise the real BusinessDayService + AppState +
MemoryRepository stack (no mocking of the logic under test), simulating
two separate sessions/devices that share only the backend repository --
exactly like two phones talking to the same Supabase project.
"""
import unittest
from datetime import datetime
from unittest.mock import patch

from backend.state import AppState
from backend.memory_repository import MemoryRepository
from backend.repository import DuplicateBusinessDayError
from models import BusinessDay, BusinessDayStatus
from services.business_day_service import BusinessDayService, BusinessDayError


def _shared_repo(business_id="biz-1") -> MemoryRepository:
    repo = MemoryRepository()
    repo.set_business_id(business_id)
    return repo


class ExistingOpenDayTests(unittest.TestCase):
    """1. Existing OPEN day (opened by someone else) -> the next caller
    proceeds by reusing it, WITHOUT attempting an INSERT."""

    def test_worker_reuses_existing_open_day_without_inserting(self):
        repo = _shared_repo()

        # Co-owner opens the day first, on their own session.
        co_owner_state = AppState(repo)
        co_owner_service = BusinessDayService(co_owner_state)
        opened_by_co_owner = co_owner_service.open_day("coowner@biz.com", "Float: 2000")

        # Worker logs in on a *different* session -- a fresh AppState
        # wrapping the same repo, with an empty local cache, exactly like
        # a separate device that hasn't synced yet.
        worker_state = AppState(repo)
        worker_service = BusinessDayService(worker_state)

        self.assertFalse(worker_state.is_business_day_open(),
                          "sanity check: worker's local cache starts stale/empty")

        with patch.object(repo, "open_business_day", wraps=repo.open_business_day) as insert_spy:
            result = worker_service.open_day("worker@biz.com", "")

        insert_spy.assert_not_called()
        self.assertEqual(result.id, opened_by_co_owner.id)
        self.assertEqual(result.opened_by, "coowner@biz.com")
        self.assertTrue(worker_state.is_business_day_open())
        # Only one row ever exists for the business.
        self.assertEqual(len(repo.list_business_days()), 1)

    def test_works_identically_for_owner_co_owner_and_worker_roles(self):
        """Business Day is business-wide -- role must not affect the
        reuse behavior."""
        repo = _shared_repo()
        opener_state = AppState(repo)
        opened = BusinessDayService(opener_state).open_day("owner@biz.com", "")

        for role_email in ("coowner@biz.com", "worker1@biz.com", "worker2@biz.com"):
            session_state = AppState(repo)
            session_service = BusinessDayService(session_state)
            with patch.object(repo, "open_business_day", wraps=repo.open_business_day) as spy:
                result = session_service.open_day(role_email, "")
            spy.assert_not_called()
            self.assertEqual(result.id, opened.id)


class NoOpenDayTests(unittest.TestCase):
    """2. No OPEN day exists -> a new one IS created."""

    def test_creates_new_day_when_none_open(self):
        repo = _shared_repo()
        state = AppState(repo)
        service = BusinessDayService(state)

        self.assertIsNone(repo.get_open_business_day())

        with patch.object(repo, "open_business_day", wraps=repo.open_business_day) as insert_spy:
            result = service.open_day("owner@biz.com", "Opening float")

        insert_spy.assert_called_once()
        self.assertEqual(result.status, BusinessDayStatus.OPEN)
        self.assertEqual(result.opened_by, "owner@biz.com")
        self.assertIsNotNone(repo.get_open_business_day())
        self.assertEqual(repo.get_open_business_day().id, result.id)

    def test_creates_new_day_after_previous_one_closed(self):
        repo = _shared_repo()
        state = AppState(repo)
        service = BusinessDayService(state)

        service.open_day("owner@biz.com", "")
        state.close_business_day("owner@biz.com", "End of day")
        self.assertIsNone(repo.get_open_business_day())

        with patch.object(repo, "open_business_day", wraps=repo.open_business_day) as insert_spy:
            second = service.open_day("worker@biz.com", "")

        insert_spy.assert_called_once()
        self.assertEqual(second.status, BusinessDayStatus.OPEN)
        self.assertEqual(second.opened_by, "worker@biz.com")
        self.assertEqual(repo.get_open_business_day().id, second.id)
        # Two rows total now exist for the business: one CLOSED, one OPEN.
        self.assertEqual(len(repo.list_business_days()), 2)


class RaceConditionTests(unittest.TestCase):
    """3. Duplicate/race condition -> handled safely: no error surfaces,
    no second row is created, and the caller gets back the day that
    actually won the race."""

    def test_simultaneous_open_resolves_to_the_winning_day_without_raising(self):
        repo = _shared_repo()
        state = AppState(repo)
        service = BusinessDayService(state)

        winning_day = BusinessDay(
            id="BD-RIVAL", opened_at=datetime.now().isoformat(),
            opened_by="rival-device@biz.com", status=BusinessDayStatus.OPEN,
            opening_note="",
        )

        # Simulate the true TOCTOU race:
        #   1. Our authoritative check (sync_open_business_day) runs and
        #      finds nothing open yet.
        #   2. Before our INSERT lands, a rival session's day lands first.
        #   3. Our INSERT hits the DB's unique constraint and the
        #      repository raises DuplicateBusinessDayError.
        #   4. We re-check the authoritative state and now see the rival's
        #      day -- and reuse it instead of erroring out.
        get_open_calls = {"n": 0}
        real_get_open = repo.get_open_business_day

        def flaky_get_open():
            get_open_calls["n"] += 1
            if get_open_calls["n"] == 1:
                return None  # first (pre-insert) check: nothing open yet
            return real_get_open()  # later checks see the real DB state

        def racing_insert(business_day):
            # The rival's write "wins" and lands in the DB right as ours
            # is rejected.
            repo._business_days.append(winning_day)
            raise DuplicateBusinessDayError(
                'duplicate key value violates unique constraint '
                '"one_open_business_day_per_business"'
            )

        with patch.object(repo, "get_open_business_day", side_effect=flaky_get_open), \
             patch.object(repo, "open_business_day", side_effect=racing_insert):
            result = service.open_day("worker@biz.com", "")

        self.assertEqual(result.id, winning_day.id)
        self.assertEqual(result.opened_by, "rival-device@biz.com")
        self.assertTrue(state.is_business_day_open())
        # No duplicate row was permanently created by our side.
        self.assertEqual(len(repo.list_business_days()), 1)

    def test_race_with_no_resolution_raises_business_day_error(self):
        """Defensive fallback: if the repository raises
        DuplicateBusinessDayError but a re-check still can't find an open
        day (shouldn't happen against a real DB, but the client must not
        pretend to succeed), a clear BusinessDayError is raised instead of
        silently swallowing it."""
        repo = _shared_repo()
        state = AppState(repo)
        service = BusinessDayService(state)

        def always_none(*_a, **_kw):
            return None

        def raising_insert(*_a, **_kw):
            raise DuplicateBusinessDayError("unique_violation")

        with patch.object(repo, "get_open_business_day", side_effect=always_none), \
             patch.object(repo, "open_business_day", side_effect=raising_insert):
            with self.assertRaises(BusinessDayError):
                service.open_day("worker@biz.com", "")


if __name__ == "__main__":
    unittest.main()
