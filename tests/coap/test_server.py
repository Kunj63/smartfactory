"""
Tests for Task 2.1 — CoAP Server
Do not modify this file.
"""

import asyncio
import json
import pytest
import aiocoap
from aiocoap import Message, Code


SERVER_URI = "coap://127.0.0.1"


@pytest.fixture
async def coap_client():
    ctx = await aiocoap.Context.create_client_context()
    yield ctx
    await ctx.shutdown()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_line1_temperature(coap_client):
    """GET /factory/line1/temperature must return 2.05 with JSON payload."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/factory/line1/temperature")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT, f"Expected 2.05 Content, got {resp.code}"
    assert resp.opt.content_format == 50, "Content-Format must be 50 (application/json)"

    data = json.loads(resp.payload.decode())
    assert "value" in data, "Payload must contain 'value'"
    assert "unit"  in data, "Payload must contain 'unit'"
    assert "ts"    in data, "Payload must contain 'ts'"
    assert data["unit"] == "C", f"Temperature unit must be 'C', got '{data['unit']}'"


@pytest.mark.asyncio
async def test_get_line2_temperature(coap_client):
    """GET /factory/line2/temperature must return 2.05 with JSON payload."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/factory/line2/temperature")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    data = json.loads(resp.payload.decode())
    assert "value" in data
    assert data["unit"] == "C"


@pytest.mark.asyncio
async def test_get_vibration(coap_client):
    """GET /factory/line1/vibration must return JSON with mm/s unit."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/factory/line1/vibration")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    data = json.loads(resp.payload.decode())
    assert data["unit"] == "mm/s"


@pytest.mark.asyncio
async def test_get_power(coap_client):
    """GET /factory/line1/power must return JSON with kW unit."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/factory/line1/power")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    data = json.loads(resp.payload.decode())
    assert data["unit"] == "kW"


@pytest.mark.asyncio
async def test_get_actuator(coap_client):
    """GET /actuator/line1/fan must return current state (ON or OFF)."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/actuator/line1/fan")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    data = json.loads(resp.payload.decode())
    assert "state" in data
    assert data["state"] in ("ON", "OFF")


@pytest.mark.asyncio
async def test_put_actuator_on(coap_client):
    """PUT /actuator/line1/fan with {"state":"ON"} must return 2.04 Changed."""
    req = Message(
        code=Code.PUT,
        uri=f"{SERVER_URI}/actuator/line1/fan",
        payload=json.dumps({"state": "ON"}).encode(),
        content_format=50,
    )
    resp = await coap_client.request(req).response
    assert resp.code == Code.CHANGED, f"Expected 2.04 Changed, got {resp.code}"

    # Verify state was actually updated
    get_req  = Message(code=Code.GET, uri=f"{SERVER_URI}/actuator/line1/fan")
    get_resp = await coap_client.request(get_req).response
    data     = json.loads(get_resp.payload.decode())
    assert data["state"] == "ON"


@pytest.mark.asyncio
async def test_put_actuator_off(coap_client):
    """PUT /actuator/line1/fan with {"state":"OFF"} must return 2.04 Changed."""
    req = Message(
        code=Code.PUT,
        uri=f"{SERVER_URI}/actuator/line1/fan",
        payload=json.dumps({"state": "OFF"}).encode(),
        content_format=50,
    )
    resp = await coap_client.request(req).response
    assert resp.code == Code.CHANGED


@pytest.mark.asyncio
async def test_put_actuator_bad_request(coap_client):
    """PUT with invalid state must return 4.00 Bad Request."""
    req = Message(
        code=Code.PUT,
        uri=f"{SERVER_URI}/actuator/line1/fan",
        payload=json.dumps({"state": "MAYBE"}).encode(),
        content_format=50,
    )
    resp = await coap_client.request(req).response
    assert resp.code == Code.BAD_REQUEST, (
        f"Expected 4.00 Bad Request for invalid state, got {resp.code}"
    )


@pytest.mark.asyncio
async def test_block2_manifest(coap_client):
    """GET /factory/manifest must return >= 3072 bytes (triggers Block2)."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/factory/manifest")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    assert len(resp.payload) >= 3072, (
        f"Manifest must be >= 3072 bytes for Block2, got {len(resp.payload)}"
    )
    assert resp.opt.content_format == 50

    data = json.loads(resp.payload.decode())
    assert "firmware_entries" in data
    assert len(data["firmware_entries"]) > 0


@pytest.mark.asyncio
async def test_well_known_core(coap_client):
    """GET /.well-known/core must return a CoRE link-format response."""
    req  = Message(code=Code.GET, uri=f"{SERVER_URI}/.well-known/core")
    resp = await coap_client.request(req).response

    assert resp.code == Code.CONTENT
    # CoRE Link Format is content-format 40
    assert resp.opt.content_format == 40, (
        f"Expected content-format 40 (CoRE Link Format), got {resp.opt.content_format}"
    )
    body = resp.payload.decode()
    assert "/factory" in body or "factory" in body
