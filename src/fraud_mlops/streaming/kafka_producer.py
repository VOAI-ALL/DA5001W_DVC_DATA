from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from confluent_kafka import Producer

from fraud_mlops.config import DATA_PATH, FEATURE_COLUMNS


def stream_transactions(
    data_path: Path,
    bootstrap_servers: str,
    topic: str,
    delay_seconds: float,
    limit: int | None,
) -> None:
    producer = Producer({"bootstrap.servers": bootstrap_servers})

    sent = 0
    for chunk in pd.read_csv(data_path, chunksize=1000):
        for _, row in chunk.iterrows():
            message = {column: float(row[column]) for column in FEATURE_COLUMNS}
            producer.produce(topic, value=json.dumps(message).encode("utf-8"))
            producer.poll(0)
            sent += 1
            if delay_seconds:
                time.sleep(delay_seconds)
            if limit and sent >= limit:
                producer.flush()
                print(f"Published {sent} transactions to {topic}.")
                return

    producer.flush()
    print(f"Published {sent} transactions to {topic}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay credit card transactions into Kafka.")
    parser.add_argument("--data-path", type=Path, default=DATA_PATH)
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default="credit-card-transactions")
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    stream_transactions(args.data_path, args.bootstrap_servers, args.topic, args.delay_seconds, args.limit)


if __name__ == "__main__":
    main()
