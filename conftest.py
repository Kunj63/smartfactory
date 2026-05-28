"""
Root conftest.py — runs before all tests.
Switches asyncio to SelectorEventLoop on Windows for aiocoap UDP support.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
