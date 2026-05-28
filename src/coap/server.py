
import asyncio
import json
import logging
import random
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource
from aiocoap import Code, Message

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s"
)
log = logging.getLogger(__name__)



SENSOR_CONFIG = {
    "temperature": {"unit": "C",    "base": 70.0, "noise": 3.0},
    "vibration":   {"unit": "mm/s", "base": 1.2,  "noise": 0.3},
    "power":       {"unit": "kW",   "base": 45.0, "noise": 5.0},
}

def _sim(sensor: str) -> dict:
    cfg = SENSOR_CONFIG[sensor]
    return {
        "value": round(cfg["base"] + random.gauss(0, cfg["noise"]), 3),
        "unit":  cfg["unit"],
        "ts":    datetime.now(timezone.utc).isoformat(),
    }

def _json(data: dict) -> bytes:
    return json.dumps(data).encode()




class SensorResource(resource.ObservableResource):
    """
    An observable CoAP resource that represents a single sensor on a line.

    TODO 1 — implemented below.
    """

    def __init__(self, line: str, sensor_type: str):
        super().__init__()
        self.line        = line
        self.sensor_type = sensor_type
        self._reading    = _sim(sensor_type)
     
        asyncio.ensure_future(self._update_loop())

    async def _update_loop(self) -> None:
        """
        TODO 2: Every 5 seconds, simulate a new reading and notify observers.
        """
        while True:
            await asyncio.sleep(5)
            self._reading = _sim(self.sensor_type)
            log.debug(
                "Updated %s/%s: %s %s",
                self.line, self.sensor_type,
                self._reading["value"], self._reading["unit"],
            )
      
            self.updated_state()

    async def render_get(self, request: Message) -> Message:
        """
        TODO 3: Return the current sensor reading as a JSON response.
        Content-Format 50 = application/json
        """
        return Message(
            code=Code.CONTENT,
            payload=_json(self._reading),
            content_format=50,
        )




class ActuatorResource(resource.Resource):
    """
    A CoAP resource representing a controllable fan actuator.

    TODO 4 — implemented below.
    """

    def __init__(self):
        super().__init__()
        self._state = "OFF"

    async def render_get(self, request: Message) -> Message:
        """TODO 5: Return current fan state as JSON."""
        return Message(
            code=Code.CONTENT,
            payload=_json({"state": self._state}),
            content_format=50,
        )

    async def render_put(self, request: Message) -> Message:
        """TODO 6: Accept ON/OFF command and update state."""
        try:
            data = json.loads(request.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return Message(
                code=Code.BAD_REQUEST,
                payload=b"Malformed JSON payload",
            )

        new_state = data.get("state", "").upper()
        if new_state not in ("ON", "OFF"):
            return Message(
                code=Code.BAD_REQUEST,
                payload=b'Invalid state: must be "ON" or "OFF"',
            )

        self._state = new_state
        log.info("Actuator fan set to %s", self._state)
        return Message(code=Code.CHANGED)




class ManifestResource(resource.Resource):
    """
    A large resource that triggers CoAP Block2 transfer.

    TODO 7 — implemented below.
    The payload is built once at class level to avoid repeated generation.
    """

    _PAYLOAD: bytes = b"" 

    @classmethod
    def _build_payload(cls) -> bytes:
        if cls._PAYLOAD:
            return cls._PAYLOAD

        entries = []
        sensor_types = ["temperature", "vibration", "power", "humidity", "pressure"]
        for i in range(60):
            s_type = sensor_types[i % len(sensor_types)]
            entries.append({
                "id":           f"sensor-fw-{i:04d}",
                "sensor_type":  s_type,
                "hw_revision":  f"REV-{chr(65 + (i % 26))}",
                "fw_version":   f"{2 + i // 20}.{(i // 4) % 10}.{i % 4}",
                "checksum_sha256": (
                    f"{'a' * 8}{i:04x}{'b' * 8}{i * 7 % 65536:04x}"
                    f"{'c' * 8}{i * 13 % 65536:04x}{'d' * 4}"
                ),
                "download_url": (
                    f"https://firmware.smartfactory.io/releases/"
                    f"v{2 + i // 20}/{s_type}/sensor-fw-{i:04d}.bin"
                ),
                "size_bytes":   131072 + i * 2048,
                "release_date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                "changelog":    (
                    f"Release {i}: stability improvements, reduced power consumption "
                    f"by {i % 15 + 1}%, fixed edge-case NaN in {s_type} ADC pipeline, "
                    f"updated bootloader to v3.{i % 10}, improved OTA retry logic."
                ),
                "compatible_hw": [f"REV-{chr(65 + j)}" for j in range(i % 4 + 1)],
                "signature":     f"ECDSA-P256:{('fe' * 32)}",
            })

        manifest = {
            "schema_version": "2.0",
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "generator":      "SmartFactory Firmware Registry v4.1",
            "total_entries":  len(entries),
            "firmware_entries": entries,
        }
        cls._PAYLOAD = json.dumps(manifest, indent=2).encode("utf-8")
        return cls._PAYLOAD

    async def render_get(self, request: Message) -> Message:
        """TODO 8: Return a >= 3 KB JSON firmware manifest."""
        payload = self._build_payload()
        assert len(payload) >= 3072, (
            f"Manifest payload too small: {len(payload)} bytes (need >= 3072)"
        )
        log.info("Serving manifest: %d bytes", len(payload))
        return Message(
            code=Code.CONTENT,
            payload=payload,
            content_format=50,
        )



async def build_server() -> aiocoap.Context:
    """
    TODO 9: Build the CoAP resource tree and create the server context.
    """
    root = resource.Site()

  
    root.add_resource(
        ["factory", "line1", "temperature"],
        SensorResource("line1", "temperature"),
    )
    root.add_resource(
        ["factory", "line1", "vibration"],
        SensorResource("line1", "vibration"),
    )
    root.add_resource(
        ["factory", "line1", "power"],
        SensorResource("line1", "power"),
    )
    root.add_resource(
        ["factory", "line2", "temperature"],
        SensorResource("line2", "temperature"),
    )


    root.add_resource(
        ["actuator", "line1", "fan"],
        ActuatorResource(),
    )

 
    root.add_resource(
        ["factory", "manifest"],
        ManifestResource(),
    )

 
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )


    context = await aiocoap.Context.create_server_context(root, bind=("127.0.0.1", 5683))
    return context


async def main() -> None:
    context = await build_server()
    log.info("CoAP server running on coap://localhost:5683")
    log.info(
        "Resources: /factory/line{1,2}/{temperature,vibration,power}, "
        "/actuator/line1/fan, /factory/manifest"
    )
 
    await asyncio.get_event_loop().create_future()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
