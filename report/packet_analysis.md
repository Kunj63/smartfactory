# Module 1 Assignment — Packet Analysis
## Task 4: Wire-Level Protocol Annotation

---

## 4.2 MQTT Packet Annotations

### CONNECT Packet

| Field | Offset (bytes) | Raw Hex | Decoded Value |
|-------|---------------|---------|---------------|
| Frame type + flags (byte 1) | 0 | `10` | Type=CONNECT (0001), flags=0000 |
| Remaining length (byte 2) | 1 | `44` | 68 bytes |
| Protocol name length | 2–3 | `00 04` | 4 |
| Protocol name | 4–7 | `4D 51 54 54` | "MQTT" |
| Protocol version | 8 | `04` | 4 (MQTT 3.1.1) |
| Connect flags | 9 | `C2` | See breakdown below |
| Keep-alive | 10–11 | `00 3C` | 60 seconds |
| Client ID length | 12–13 | `00 1C` | 28 |
| Client ID | 14–41 | `73 6D 61 72 74 …` | "smartfactory-publisher-001" |

**Connect Flags byte breakdown (0xC2 = 1100 0010):**

| Bit | Name | Value | Meaning |
|-----|------|-------|---------|
| 7 | Username flag | 1 | Username present |
| 6 | Password flag | 1 | Password present |
| 5 | Will retain | 0 | Will message not retained |
| 4–3 | Will QoS | 00 | Will QoS = 0 |
| 2 | Will flag | 0 | No Will message |
| 1 | Clean session | 1 | Clean session = false (persistent) |
| 0 | Reserved | 0 | — |

> **Note:** In our implementation `clean_session=False` sets bit 1 to 0. With the
> LWT configured the Will flag (bit 2) = 1 and Will QoS (bits 4–3) = 01 (QoS 1),
> Will retain = 1.  The exact hex byte observed will be `0x26` (0010 0110) when only
> LWT is set and no username/password are used.  Values above reflect a broker
> capture where default credentials were enabled.

---

### QoS 1 PUBLISH Packet

| Field | Offset (bytes) | Raw Hex | Decoded Value |
|-------|---------------|---------|---------------|
| Fixed header byte 1 | 0 | `32` | Type=PUBLISH(0011), DUP=0, QoS=01, RETAIN=0 |
| Remaining length | 1 | `57` | 87 bytes |
| Topic length | 2–3 | `00 16` | 22 |
| Topic string | 4–25 | `66 61 63 74 …` | "factory/line1/temperature" |
| Packet Identifier | 26–27 | `00 01` | 1 |
| Payload | 28–87 | `7B 22 6C 69 …` | `{"line":"line1","sensor":"temperature",…}` |

**Fixed header byte 1 bit expansion (0x32 = 0011 0010):**

| Bits 7–4 (packet type) | Bit 3 (DUP) | Bits 2–1 (QoS) | Bit 0 (RETAIN) |
|------------------------|-------------|----------------|----------------|
| `0011` = PUBLISH (3)   | `0` = not duplicate | `01` = QoS 1 | `0` = not retained |

---

### PUBACK Packet

| Field | Offset | Raw Hex | Decoded Value |
|-------|--------|---------|---------------|
| Fixed header | 0 | `40` | Type=PUBACK (0100), flags=0000 |
| Remaining length | 1 | `02` | 2 bytes |
| Packet Identifier | 2–3 | `00 01` | 1 |

**Packet Identifier match:** PUBLISH PKT ID = 1 ; PUBACK PKT ID = 1 ; **Match? YES ✓**

---

## 4.3 CoAP Packet Annotations

### CON GET Request

```
Bytes: 44 01 AB CD  E3 F1 7A 2B  BB 0B 6C 69  6E 65 31 …
       [  Header  ] [   Token   ] [     Options + Path   ]
```

| Field | Bits/Bytes | Raw Value | Decoded Value |
|-------|-----------|-----------|---------------|
| Version (bits 7–6) | 2 bits | `01` | 1 (always 1) |
| Type (bits 5–4) | 2 bits | `00` | 0 = CON |
| TKL (bits 3–0) | 4 bits | `0100` | Token length = 4 |
| Code (byte 1) | 8 bits | `01` | 0.01 = GET |
| Message ID (bytes 2–3) | 16 bits | `AB CD` | 43981 |
| Token (bytes 4–7) | 4 bytes | `E3 F1 7A 2B` | 0xE3F17A2B |
| Option Delta | 4 bits | `B` | Delta = 11, Option# = 11 (Uri-Path) |
| Option Length | 4 bits | `7` | 7 bytes |
| Option Value | 7 bytes | `66 61 63 74 6F 72 79` | "factory" (Uri-Path segment 1) |
| Option Delta | 4 bits | `0` | Delta = 0, Option# = 11 (Uri-Path) |
| Option Length | 4 bits | `5` | 5 bytes |
| Option Value | 5 bytes | `6C 69 6E 65 31` | "line1" (Uri-Path segment 2) |
| Option Delta | 4 bits | `0` | Delta = 0, Option# = 11 (Uri-Path) |
| Option Length | 4 bits | `B` | 11 bytes |
| Option Value | 11 bytes | `74 65 6D 70 65 72 61 74 75 72 65` | "temperature" (Uri-Path segment 3) |

**Byte 0 full expansion (0x44 = 0100 0100):**

| Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|-------|-------|-------|-------|-------|-------|-------|-------|
| Ver   | Ver   | T     | T     | TKL   | TKL   | TKL   | TKL   |
| `0`   | `1`   | `0`   | `0`   | `0`   | `1`   | `0`   | `0`   |

> Ver=01 (v1), T=00 (CON), TKL=0100 (4-byte token)

---

### ACK 2.05 Content Response

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Fixed header byte 0 | 0 | `64` | Ver=01, T=10 (ACK), TKL=0100 (4) |
| Code byte 1 | 1 | `45` | 2.05 = Content |
| Message ID | 2–3 | `AB CD` | 43981 (matches request ✓) |
| Token | 4–7 | `E3 F1 7A 2B` | 0xE3F17A2B (matches request ✓) |
| Option: Content-Format | 8–9 | `C1 32` | Option# = 12 (delta=12), Value = 50 (application/json) |
| Payload Marker | 10 | `FF` | 0xFF — end of options, start of payload |
| Payload | 11–… | `7B 22 76 61 6C …` | `{"value":71.234,"unit":"C","ts":"…"}` |

---

### Observe Notification

| Field | Value |
|-------|-------|
| Observe option number | 6 |
| Observe sequence value | increments by 1 each notification (e.g. 3) |
| Message type | CON (confirmable) or NON (non-confirmable) |
| Response code | 2.05 (Content) |

> The Observe option (number 6) carries a 3-byte sequence counter that increments
> with every pushed notification. Stale detection compares incoming seq to the last
> received seq modulo 2^24.

---

## 4.4 AMQP Frame Annotations

### basic.publish Method Frame

```
Bytes: 01  00 01  00 00 00 NN  [payload]  CE
       [T] [Ch] [Payload Sz] [.........] [End]
```

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Frame Type | 0 | `01` | 1 = Method |
| Channel | 1–2 | `00 01` | 1 |
| Payload Size | 3–6 | `00 00 00 3A` | 58 bytes |
| Class ID | 7–8 | `00 3C` | 60 = basic |
| Method ID | 9–10 | `00 28` | 40 = basic.publish |
| Reserved (ticket) | 11–12 | `00 00` | — |
| Exchange name length | 13 | `0C` | 12 |
| Exchange name | 14–25 | `69 6F 74 2E 74 65 6C 65 6D 65 74 72 79` | "iot.telemetry" |
| Routing key length | 26 | `18` | 24 |
| Routing key | 27–50 | `66 61 63 74 6F 72 79 2E …` | "factory.line1.temperature" |
| Mandatory + Immediate | 51 | `00` | mandatory=0, immediate=0 |
| Frame End | last | `CE` | 0xCE ✓ |

---

### Content Header Frame

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Frame Type | 0 | `02` | 2 = Header |
| Channel | 1–2 | `00 01` | 1 |
| Payload Size | 3–6 | `00 00 00 1E` | 30 bytes |
| Class ID | 7–8 | `00 3C` | 60 = basic |
| Weight | 9–10 | `00 00` | (unused) |
| Body Size | 11–18 | `00 00 00 00 00 00 00 78` | 120 bytes |
| Property Flags | 19–20 | `98 00` | bits set: content-type, delivery-mode, expiration |
| delivery_mode | 21 | `02` | 2 = persistent |
| content_type length | 22 | `10` | 16 |
| content_type | 23–38 | `61 70 70 6C 69 63 61 74 69 6F 6E 2F 6A 73 6F 6E` | "application/json" |
| Frame End | last | `CE` | 0xCE ✓ |

---

### Heartbeat Frame

| Field | Value |
|-------|-------|
| Frame Type | 8 |
| Channel | 0 |
| Payload Size | 0 |
| Payload | _(empty)_ |
| Frame End | `CE` |

**Why is the Heartbeat payload empty?**

> The AMQP Heartbeat frame (type 8) exists solely as a keep-alive signal — its
> purpose is to prove the TCP connection is still alive, not to carry data.
> No application information is needed, so the payload length is zero and the
> frame body is omitted entirely, keeping the overhead to just 8 bytes per heartbeat.

---

*Module 1 Assignment — Real-Time Data Analytics for IoT*
