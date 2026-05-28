"""
conftest.py — pytest configuration
Fixes aiocoap UDP issues on Windows by switching to SelectorEventLoop.
"""
import asyncio
import sys
import pytest


if sys.platform == "win32":
    # aiocoap requires SelectorEventLoop on Windows — ProactorEventLoop
    # (the default on Windows) does not support UDP properly with aiocoap.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()
