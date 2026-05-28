"""
Tests for Task 1.3 — QoS Loss Experiment
Do not modify this file.
Run with: pytest tests/mqtt/test_qos_loss.py -v -s
"""

import json
import time
import threading
import statistics
import pytest
import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TEST_TOPIC  = "test/qos_experiment"
NUM_MSGS    = 50   # messages per QoS level
MSG_DELAY   = 0.05  # seconds between messages


def _run_qos_experiment(qos: int) -> dict:
    """Send NUM_MSGS at the given QoS and return stats."""
    received   = []
    latencies  = []
    send_times = {}
    done       = threading.Event()

    sub = mqtt.Client(client_id=f"test-sub-qos{qos}", clean_session=True)

    def on_connect(client, userdata, flags, rc):
        client.subscribe(TEST_TOPIC, qos=qos)

    def on_message(client, userdata, msg):
        arrival = time.time()
        try:
            data = json.loads(msg.payload.decode())
            seq  = data["seq"]
            if seq in send_times:
                latencies.append((arrival - send_times[seq]) * 1000)
            received.append(seq)
        except Exception:
            pass
        if len(received) >= NUM_MSGS or (received and max(received) >= NUM_MSGS - 1):
            done.set()

    sub.on_connect = on_connect
    sub.on_message = on_message
    sub.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    sub.loop_start()
    time.sleep(0.3)

    pub = mqtt.Client(client_id=f"test-pub-qos{qos}", clean_session=True)
    pub.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    pub.loop_start()
    time.sleep(0.2)

    for i in range(NUM_MSGS):
        payload = json.dumps({"seq": i, "qos": qos}).encode()
        send_times[i] = time.time()
        pub.publish(TEST_TOPIC, payload, qos=qos)
        time.sleep(MSG_DELAY)

    done.wait(timeout=10)
    time.sleep(0.5)  # allow stragglers

    pub.loop_stop(); pub.disconnect()
    sub.loop_stop(); sub.disconnect()

    recv_count  = len(set(received))          # unique messages
    duplicates  = len(received) - recv_count  # extras
    lost        = NUM_MSGS - recv_count
    loss_pct    = round(lost / NUM_MSGS * 100, 1)
    avg_latency = round(statistics.mean(latencies), 2) if latencies else 0.0

    return {
        "qos":         qos,
        "sent":        NUM_MSGS,
        "received":    recv_count,
        "lost":        lost,
        "loss_pct":    loss_pct,
        "duplicates":  duplicates,
        "avg_latency": avg_latency,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_qos_experiment_and_print_table():
    """
    Run QoS 0, 1, and 2 experiments and print a results table.
    NOTE: This test does NOT simulate packet loss (tc netem not available on Windows).
    Results show baseline behaviour; loss column should be ~0 on a local broker.
    """
    results = []
    for qos in (0, 1, 2):
        print(f"\nRunning QoS {qos} experiment ({NUM_MSGS} messages)…")
        r = _run_qos_experiment(qos)
        results.append(r)
        print(f"  QoS {qos}: sent={r['sent']} recv={r['received']} "
              f"lost={r['lost']} ({r['loss_pct']}%) "
              f"dups={r['duplicates']} latency={r['avg_latency']}ms")

    # Print the summary table
    print("\n")
    print("=" * 75)
    print(f"{'Protocol / QoS':<25} {'Sent':>6} {'Received':>10} "
          f"{'Lost (%)':>10} {'Duplicates':>12} {'Avg Latency (ms)':>18}")
    print("-" * 75)
    for r in results:
        print(f"{'MQTT QoS ' + str(r['qos']):<25} {r['sent']:>6} {r['received']:>10} "
              f"{str(r['loss_pct'])+'%':>10} {r['duplicates']:>12} {r['avg_latency']:>18}")
    print("=" * 75)
    print("\nCopy the table above into report/comparison_report.md Section 5.1")

    # Assertions — on a local broker without artificial loss all should deliver
    for r in results:
        assert r["received"] > 0, f"QoS {r['qos']}: no messages received at all"

    # QoS 1 and 2 must deliver everything on a lossless loopback
    assert results[1]["lost"] == 0, "QoS 1 should have zero loss on local broker"
    assert results[2]["lost"] == 0, "QoS 2 should have zero loss on local broker"
    # QoS 2 must have zero duplicates
    assert results[2]["duplicates"] == 0, "QoS 2 must never produce duplicates"
