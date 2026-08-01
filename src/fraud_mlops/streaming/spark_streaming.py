from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import DoubleType, StructField, StructType

from fraud_mlops.config import FEATURE_COLUMNS


def build_schema() -> StructType:
    return StructType([StructField(column, DoubleType(), nullable=False) for column in FEATURE_COLUMNS])


def main() -> None:
    parser = argparse.ArgumentParser(description="Consume transaction stream from Kafka with Spark.")
    parser.add_argument("--bootstrap-servers", default="localhost:9092")
    parser.add_argument("--topic", default="credit-card-transactions")
    parser.add_argument("--checkpoint", default="data/processed/spark-checkpoints/fraud-stream")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("credit-card-fraud-stream")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap_servers)
        .option("subscribe", args.topic)
        .option("startingOffsets", "latest")
        .load()
    )

    parsed = raw.select(from_json(col("value").cast("string"), build_schema()).alias("transaction")).select(
        "transaction.*"
    )

    query = (
        parsed.writeStream.outputMode("append")
        .format("console")
        .option("truncate", "false")
        .option("checkpointLocation", args.checkpoint)
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()

