"""Disable accidental network access, including in mocked recognition tests."""

import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Tests must not access the network.")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.name == "test_smoke.py":
            item.add_marker(pytest.mark.slow)
