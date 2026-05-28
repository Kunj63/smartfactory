"""
Tests for Task 1.1 — MQTT Publisher
Do not modify this file.
"""

import json
import time
import threading
import pytest
import paho.mqtt.client as mqtt

from src.mqtt.publisher import SmartFactoryPublisher, LINES, SENSORS, CLIENT_ID, SensorReading


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def publisher():
    pub = SmartFactoryPublisher()
    yield pub
    try:
        pub.disconnect()
    except Exception:
        pass


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_connect_persistent():
    """Publisher must connect with clean_session=False (persistent session)."""
    pub = SmartFactoryPublisher()
    client = pub._build_client()
    assert client._clean_session is False, (
        "clean_session must be False for a persistent session"
    )


def test_lwt_configured():
    """Publisher must configure LWT for factory/line1/status.
    Handles both paho-mqtt v1.x (dict) and v2.x (separate attributes).
    """
    pub    = SmartFactoryPublisher()
    client = pub._build_client()

    # paho-mqtt v2.x stores will as separate private attributes
    if hasattr(client, "_will_topic"):
        topic   = client._will_topic
        payload = client._will_payload
        qos     = client._will_qos
        retain  = client._will_retain
    elif isinstance(client._will, dict):
        topic   = client._will["topic"]
        payload = client._will["payload"]
        qos     = client._will["qos"]
        retain  = client._will["retain"]
    else:
        pytest.fail("Cannot read LWT — unknown paho-mqtt version")

    # topic may be str or bytes depending on paho version
    topic_str = topic.decode() if isinstance(topic, bytes) else topic
    assert topic_str == "factory/line1/status", (
        f"LWT topic must be 'factory/line1/status', got '{topic}'"
    )
    assert payload in (b"offline", "offline"), (
        f"LWT payload must be 'offline', got '{payload}'"
    )
    assert qos == 1,       "LWT QoS must be 1"
    assert retain is True, "LWT retain must be True"


def test_topic_format():
    """_topic() must return factory/{line}/{sensor}."""
    pub = SmartFactoryPublisher()
    assert pub._topic("line1", "temperature") == "factory/line1/temperature"
    assert pub._topic("line2", "power")       == "factory/line2/power"
    assert pub._topic("line1", "vibration")   == "factory/line1/vibration"


def test_simulate_reading_fields():
    """_simulate_reading must return a SensorReading with all required fields."""
    pub     = SmartFactoryPublisher()
    reading = pub._simulate_reading("line1", "temperature")
    assert isinstance(reading, SensorReading)
    assert reading.line   == "line1"
    assert reading.sensor == "temperature"
    assert reading.unit   == "C"
    assert isinstance(reading.value, float)
    assert isinstance(reading.seq, int) and reading.seq >= 1
    assert reading.timestamp


def test_seq_increments():
    """Sequence counter must increment on each call for the same sensor."""
    pub = SmartFactoryPublisher()
    r1  = pub._simulate_reading("line1", "temperature")
    r2  = pub._simulate_reading("line1", "temperature")
    r3  = pub._simulate_reading("line1", "temperature")
    assert r2.seq == r1.seq + 1
    assert r3.seq == r2.seq + 1


def test_publishes_correct_topics():
    """publish_reading must publish to factory/{line}/{sensor}."""
    received = {}
    done     = threading.Event()

    spy = mqtt.Client(client_id="test-spy-publisher", clean_session=True)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            for line in LINES:
                for sensor in SENSORS:
                    client.subscribe(f"factory/{line}/{sensor}", qos=0)

    def on_message(client, userdata, msg):
        received[msg.topic] = json.loads(msg.payload.decode())
        if len(received) >= len(LINES) * len(SENSORS):
            done.set()

    spy.on_connect = on_connect
    spy.on_message = on_message

    try:
        spy.connect("localhost", 1883, keepalive=10)
        spy.loop_start()
        time.sleep(0.5)

        pub = SmartFactoryPublisher()
        pub.connect()

        for line in LINES:
            for sensor in SENSORS:
                reading = pub.publish_reading(line, sensor)
                assert isinstance(reading, SensorReading)

        done.wait(timeout=5)
        pub.disconnect()

        assert len(received) == len(LINES) * len(SENSORS), (
            f"Expected {len(LINES)*len(SENSORS)} topics, got {len(received)}"
        )
        for line in LINES:
            for sensor in SENSORS:
                topic = f"factory/{line}/{sensor}"
                assert topic in received
                payload = received[topic]
                assert "value"     in payload
                assert "unit"      in payload
                assert "timestamp" in payload
                assert "seq"       in payload
    finally:
        spy.loop_stop()
        spy.disconnect()


def test_qos_per_sensor():
    """Each sensor must use the correct QoS level."""
    assert SENSORS["temperature"]["qos"] == 1
    assert SENSORS["vibration"]["qos"]   == 0
    assert SENSORS["power"]["qos"]       == 2
