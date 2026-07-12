"""Exceptions shared across the wizard."""

from __future__ import annotations


class SetupAlreadyClaimed(Exception):
    """A step lost a race — another request already completed it.

    Raised by a step's ``on_complete``/``save`` when it detects, under a
    lock, that the work it was about to do has already been done. The
    generic step view catches it and re-renders the form with an error
    instead of returning HTTP 500.
    """
