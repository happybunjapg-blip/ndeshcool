"""Regression test for the Open Business Day button freeze.

Root cause: the button's on_click handler only caught BusinessDayError.
Any other exception raised by services.business_day.open_day() (e.g. a
Supabase/Postgrest APIError from an RLS rejection, schema mismatch, or a
unique-constraint violation on double-open) propagated out of the Flet
on_click handler. Flet swallows exceptions raised inside event handlers,
so the user was left stuck on the Business Day page with no error message
and no navigation to the shell.

This test simulates that exact scenario against the real handler code
(not a mock of it) and asserts that:
  1. The handler no longer raises.
  2. The user is shown an error snack bar.
  3. on_opened() (navigation to the shell) is NOT called, since the
     Business Day was not actually opened.
"""
import unittest
from unittest.mock import MagicMock, patch

from pages.worker.business_day_page import build_business_day_gate


class FakeUser:
    email = "worker@example.com"
    id = "user-123"


class OpenBusinessDayHandlerTests(unittest.TestCase):
    def _build(self, open_day_side_effect):
        services = MagicMock()
        services.business_day.open_day.side_effect = open_day_side_effect
        page = MagicMock()
        on_opened = MagicMock()
        container = build_business_day_gate(page, services, FakeUser(), on_opened)
        # The button is the last control in the card's column.
        card_column = container.content.content
        button = card_column.controls[-1]
        return button, services, page, on_opened

    @patch("pages.worker.business_day_page.show_snack")
    def test_generic_exception_does_not_propagate_and_shows_error(self, mock_show_snack):
        """A raw Supabase/Postgrest error (RLS, schema mismatch, unique
        violation on double-open, network failure, etc.) must not crash or
        silently freeze the handler."""
        button, services, page, on_opened = self._build(
            open_day_side_effect=Exception("duplicate key value violates unique constraint")
        )

        # Should NOT raise -- this is the actual bug: previously this call
        # would propagate the exception straight out of on_click.
        button.on_click(MagicMock())

        mock_show_snack.assert_called_once()
        on_opened.assert_not_called()

    @patch("pages.worker.business_day_page.show_snack")
    def test_business_day_error_still_handled(self, mock_show_snack):
        from services import BusinessDayError
        button, services, page, on_opened = self._build(
            open_day_side_effect=BusinessDayError("A Business Day is already open.")
        )
        button.on_click(MagicMock())
        mock_show_snack.assert_called_once()
        on_opened.assert_not_called()

    @patch("pages.worker.business_day_page.show_snack")
    def test_success_navigates_via_on_opened(self, mock_show_snack):
        button, services, page, on_opened = self._build(open_day_side_effect=None)
        button.on_click(MagicMock())
        mock_show_snack.assert_not_called()
        on_opened.assert_called_once()


if __name__ == "__main__":
    unittest.main()