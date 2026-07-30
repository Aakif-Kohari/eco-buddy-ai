"""Unit tests for session_state_utils module."""

import pytest
from unittest.mock import patch
import session_state_utils as ssu


def test_ensure_session_state():
    mock_state = {"a": 1}
    with patch("session_state_utils.st.session_state", mock_state):
        ssu.ensure_session_state({"a": 10, "b": 20})
        assert mock_state["a"] == 1
        assert mock_state["b"] == 20


def test_set_session_state_if_changed():
    mock_state = {"foo": "bar"}
    with patch("session_state_utils.st.session_state", mock_state):
        # Value unchanged -> returns False
        changed = ssu.set_session_state_if_changed("foo", "bar")
        assert not changed
        assert mock_state["foo"] == "bar"

        # Value changed -> returns True
        changed = ssu.set_session_state_if_changed("foo", "baz")
        assert changed
        assert mock_state["foo"] == "baz"

        # New key -> returns True
        changed = ssu.set_session_state_if_changed("new_key", 100)
        assert changed
        assert mock_state["new_key"] == 100
