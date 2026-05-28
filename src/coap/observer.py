
import asyncio
import json
import logging
from datetime import datetime, timezone

import aiocoap
from aiocoap import Message, Code

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s"
)
log = logging.getLogger(__name__)

SERVER_BASE      = "coap://127.0.0.1"
OBSERVE_DURATION = 60   


_OBS_WRAP = 1 << 24


class FactoryObserver:
    """Observes CoAP sensor resources and reassembles Block2 transfers."""

    def __init__(self):
        self._ctx  = None
        self._last_seq:   dict[str, int] = {}   
        self._stale_count: dict[str, int] = {}  
 

    async def start(self) -> None:
        """Create the aiocoap client context."""
        self._ctx = await aiocoap.Context.create_client_context()

    async def stop(self) -> None:
        """Clean up the context."""
        if self._ctx:
            await self._ctx.shutdown()

 

    async def observe_resource(self, uri: str) -> None:
        """
        TODO 1: Subscribe to a single observable CoAP resource for
        OBSERVE_DURATION seconds, then deregister cleanly.
        """
        log.info("Registering Observe on %s", uri)
        request = Message(code=Code.GET, uri=uri, observe=0)
        pr = self._ctx.request(request)

    
        async def _consume():
            async for response in pr.observation:
                self._handle_notification(uri, response)

        try:
            await asyncio.wait_for(_consume(), timeout=float(OBSERVE_DURATION))
        except asyncio.TimeoutError:
            pass
        finally:
            pr.observation.cancel()
            log.info("Deregistered from %s", uri)

    def _handle_notification(self, uri: str, response: Message) -> None:
        """
        TODO 2: Process a single Observe notification.
        """
        seq = response.opt.observe
        if seq is None:
          
            return

        last = self._last_seq.get(uri, -1)

        if last >= 0:
     
            forward_diff = (seq - last) % _OBS_WRAP
            if forward_diff == 0 or forward_diff > (_OBS_WRAP >> 1):
                self._stale_count[uri] = self._stale_count.get(uri, 0) + 1
                log.warning(
                    "STALE notification on %s: seq=%d <= last=%d", uri, seq, last
                )
                return

        self._last_seq[uri] = seq

        try:
            data  = json.loads(response.payload.decode("utf-8"))
            value = data.get("value", "?")
            unit  = data.get("unit", "")
            ts    = data.get("ts", datetime.now(timezone.utc).isoformat())
            log.info("[OBSERVE] %s  seq=%d  val=%s %s  @ %s", uri, seq, value, unit, ts)
        except (ValueError, UnicodeDecodeError):
            log.info("[OBSERVE] %s  seq=%d  payload=%r", uri, seq, response.payload)



    async def fetch_manifest(self) -> None:
        """
        TODO 3: Perform a GET on /factory/manifest and reassemble Block2.
        aiocoap handles Block2 reassembly automatically.
        """
        uri = f"{SERVER_BASE}/factory/manifest"
        log.info("Fetching manifest from %s", uri)

        request  = Message(code=Code.GET, uri=uri)
        response = await self._ctx.request(request).response

        payload = response.payload
        log.info("Manifest received: %d bytes", len(payload))

     
        try:
            data    = json.loads(payload.decode("utf-8"))
            entries = data.get("firmware_entries", data if isinstance(data, list) else [])
            count   = len(entries)
            log.info("Firmware entries in manifest: %d", count)
        except (ValueError, UnicodeDecodeError):
            log.warning("Manifest payload is not valid JSON")

      
        block2 = getattr(response.opt, "block2", None)
        if block2 is not None:
            log.info(
                "Final Block2 option: block_number=%d, size_exp=%d",
                block2.block_number, block2.size_exponent,
            )

        log.info("Block2 transfer complete")

   

    async def run(self) -> None:
        """
        TODO 4: Run both observations concurrently, then fetch the manifest.
        """
        await self.start()
        try:
   
            await asyncio.gather(
                self.observe_resource(
                    f"{SERVER_BASE}/factory/line1/temperature"
                ),
                self.observe_resource(
                    f"{SERVER_BASE}/factory/line2/temperature"
                ),
            )


            await self.fetch_manifest()


            print("\n── Stale Notification Summary ──────────────────")
            if self._stale_count:
                for uri, count in self._stale_count.items():
                    print(f"  {uri}: {count} stale notification(s)")
            else:
                print("  No stale notifications detected.")
            print("────────────────────────────────────────────────")

        finally:
            await self.stop()


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    observer = FactoryObserver()
    asyncio.run(observer.run())
# This line is intentionally left blank
