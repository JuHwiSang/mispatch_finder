import pytest
from typing import Optional

from mispatch_finder.core.usecases.show_log import ShowLogUseCase


class FakeLogStore:
    def __init__(self):
        self.read_calls = []
        self.summarize_calls = []

    def read_log(self, ghsa: str, verbose: bool) -> list[str]:
        self.read_calls.append((ghsa, verbose))
        if verbose:
            return [
                '{"message":"run_started","ghsa":"GHSA-TEST"}',
                '{"message":"final_result","payload":{"type":"final_result"}}',
            ]
        return [
            "GHSA-TEST | good/good | test reason",
        ]

    def summarize_all(self, verbose: bool) -> list[str]:
        self.summarize_calls.append(verbose)
        if verbose:
            return [
                "GHSA-1111 | good/good | reason1 | MCP: 10 calls",
                "GHSA-2222 | low/low | reason2 | MCP: 5 calls",
            ]
        return [
            "GHSA-1111 | good/good | reason1",
            "GHSA-2222 | low/low | reason2",
        ]


def test_show_log_with_ghsa_verbose():
    store = FakeLogStore()
    uc = ShowLogUseCase(log_store=store)

    result = uc.execute(ghsa="GHSA-TEST", verbose=True)

    assert store.read_calls == [("GHSA-TEST", True)]
    assert len(result) == 2
    assert "GHSA-TEST" in result[0]


def test_show_log_with_ghsa_non_verbose():
    store = FakeLogStore()
    uc = ShowLogUseCase(log_store=store)

    result = uc.execute(ghsa="GHSA-TEST", verbose=False)

    assert store.read_calls == [("GHSA-TEST", False)]
    assert len(result) == 1
    assert "GHSA-TEST" in result[0]


def test_show_log_without_ghsa_verbose():
    store = FakeLogStore()
    uc = ShowLogUseCase(log_store=store)

    result = uc.execute(ghsa=None, verbose=True)

    assert store.summarize_calls == [True]
    assert len(result) == 2
    assert "MCP: 10 calls" in result[0]


def test_show_log_without_ghsa_non_verbose():
    store = FakeLogStore()
    uc = ShowLogUseCase(log_store=store)

    result = uc.execute(ghsa=None, verbose=False)

    assert store.summarize_calls == [False]
    assert len(result) == 2
    assert "GHSA-1111" in result[0]

