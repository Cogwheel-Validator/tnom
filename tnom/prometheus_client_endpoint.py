"""Prometheus client for exposing TNOM metrics.

It has one class:
    - PrometheusMetrics: Provides Prometheus metrics for the monitoring system.
    Which has 2 funcs:
        - __init__: Initialize the Prometheus metrics.
        - update_metrics: Update the metrics from the database.

And two functions to set up FastAPI:
    - create_prometheus_client: Create and return a FastAPI app with Prometheus metrics.
    - start_metrics_server: Start the Prometheus metrics server.
"""
import asyncio
import logging
from pathlib import Path

import hypercorn.asyncio
import hypercorn.config
from database_handler import read_current_epoch_data
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, make_asgi_app


class PrometheusMetrics:
    """Provides Prometheus metrics for the monitoring system.

    This class is responsible for updating and exposing Prometheus metrics
    for the monitoring system.

    """

    def __init__(self, db_path: Path, epoch: int) -> None:
        """Initialize the Prometheus metrics.

        Args:
            db_path (Path): Path to the database file.
            epoch (int): The current epoch number.

        """
        self.db_path = db_path
        self.epoch = epoch

        namespace = "nibiru_oracle"

        self.slash_epoch = Gauge(
            f"{namespace}_slash_epoch",
            "Current epoch",
        )

        self.miss_counter_events = Gauge(
            f"{namespace}_miss_counter_events",
            "Total number of miss counter events",
        )

        self.miss_counter_events_p1_executed = Counter(
            f"{namespace}_miss_counter_events_p1_executed",
            "P1 alert executed",
        )

        self.miss_counter_events_p2_executed = Counter(
            f"{namespace}_miss_counter_events_p2_executed",
            "P2 alert executed",
        )

        self.miss_counter_events_p3_executed = Counter(
            f"{namespace}_miss_counter_events_p3_executed",
            "P3 alert executed",
        )

        self.unsigned_oracle_events = Gauge(
            f"{namespace}_unsigned_oracle_events",
            "Total number of unsigned oracle events",
        )

        self.price_feed_addr_balance = Gauge(
            f"{namespace}_price_feed_balance",
            "Price feed wallet unibi balance",
        )

        self.small_balance_alert = Counter(
            f"{namespace}_small_balance_alert_executed",
            "Small balance alert executed",
        )

        self.very_small_balance_alert = Counter(
            f"{namespace}_very_small_balance_alert_executed",
            "Very small balance alert executed",
        )

        self.consecutive_misses = Gauge(
            f"{namespace}_consecutive_misses",
            "Consecutive unsigned events.",
        )
        self.api_cons_miss = Gauge(
            f"{namespace}_api_cons_miss",
            "API detected as not working.",
        )

    def update_metrics(self) -> None:
        """Update the metrics from the database.

        Read the current epoch data from the database and update all metrics.
        If there is an error reading the data, raise a ValueError.
        """
        try:
            data = read_current_epoch_data(self.db_path, self.epoch)

            # Gauge data
            self.slash_epoch.set(data["slash_epoch"])
            self.miss_counter_events.set(data["miss_counter_events"])
            self.unsigned_oracle_events.set(data["unsigned_oracle_events"])
            self.price_feed_addr_balance.set(data["price_feed_addr_balance"])
            self.consecutive_misses.set(data["consecutive_misses"])
            self.api_cons_miss.set(data["api_cons_miss"])

            # Counter data
            self.miss_counter_events_p1_executed.inc(
                data["miss_counter_p1_executed"])
            self.miss_counter_events_p2_executed.inc(
                data["miss_counter_p2_executed"])
            self.miss_counter_events_p3_executed.inc(
                data["miss_counter_p3_executed"])
            self.small_balance_alert.inc(data["small_balance_alert_executed"])
            self.very_small_balance_alert.inc(
                data["very_small_balance_alert_executed"])
        except KeyError as e:
            msg = f"Missing data field for metrics update: {e}"
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"Error updating metrics: {e}"
            raise ValueError(msg) from e

def create_prometheus_client(metrics: PrometheusMetrics) -> FastAPI:
    """Create and return a FastAPI app with Prometheus metrics.

    This function initializes a FastAPI application and mounts a Prometheus
    metrics endpoint at '/metrics'. It updates the provided PrometheusMetrics
    instance before creating the ASGI app for Prometheus.

    Args:
        metrics (PrometheusMetrics): An instance of PrometheusMetrics to update
            and manage the metrics.

    Returns:
        FastAPI: A FastAPI application with Prometheus metrics endpoint mounted.

    """
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None, # no need for documentation since API
        #is only used to communicate with Prometheus
    )
    metrics.update_metrics()
    metrics_app = make_asgi_app()
    app.mount ("/metrics", metrics_app)
    return app

async def start_metrics_server(
    metrics: PrometheusMetrics,
    prometheus_host: str,
    prometheus_port: int,
    shutdown_event: asyncio.Event,
) -> None:
    """Start the Prometheus metrics server.

    This function starts a metrics server using the Hypercorn ASGI server.
    The metrics are collected from the given `metrics` object.
    The server will listen on the given `prometheus_port` at the given
    `prometheus_host` and on localhost:7130.

    Args:
        metrics (PrometheusMetrics): The metrics object to collect metrics from.
        prometheus_port (int): The port to listen on.
        prometheus_host (str): The hostname to listen on.
        shutdown_event (asyncio.Event): An event to notify when the server
            should shutdown.

    Returns:
        None

    """
    config = hypercorn.config.Config()
    config.bind = []
    if prometheus_host and prometheus_port:
        config.bind.append(f"{prometheus_host}:{prometheus_port}")
    else:
        config.bind.append("127.0.0.1:7130")
    config.graceful_timeout = 5
    config.workers = 1
    config.shutdown_timeout = 10

    app = create_prometheus_client(metrics)
    async def shutdown_trigger() -> None:
        """Wait for the shutdown event to be set.

        This function waits asynchronously for the `shutdown_event` to be set,
        indicating that the server should shut down.

        """
        await shutdown_event.wait()

    try:
        await hypercorn.asyncio.serve(
            app,
            config,
            mode="asgi",
            shutdown_trigger=shutdown_trigger)
    except asyncio.CancelledError:
        logging.info("Prometheus server task cancelled.")
        # Hypercorn's serve function doesn't automatically clean up
        # Make sure to release resources if necessary here.
    finally:
        logging.info("Prometheus server shutting down.")
