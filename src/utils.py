"""Utility classes and functions for the exporter."""

import datetime
from typing import NamedTuple

from prometheus_client import Gauge, Info


class TestResult(NamedTuple):
    """
    Result of a speedtest.

    Note that constructing this with no attributes should only be used in the
    case of an error.
    """

    server_city: str = ""
    server_region: str = ""
    ping: float = 0
    jitter: float = 0
    download_mbps: float = 0
    download_bps: int = 0
    upload_mbps: float = 0
    upload_bps: int = 0
    status: int = 0

    def __repr__(self) -> str:
        """Produce a readable representation of a test result with units."""
        return (
            "TestResult("
            f"Server city = {self.server_city}, "
            f"Server region = {self.server_region}, "
            f"Jitter = {self.jitter} ms, "
            f"Ping = {self.ping} ms, "
            f"Download = {self.download_mbps} Mbit/s, "
            f"Upload = {self.upload_mbps} Mbit/s"
            ")"
        )


class Metrics:
    """Prometheus metrics from a speedtest."""

    def __init__(self, cache_secs: int) -> None:
        """Instantiate the metrics."""
        self.server = Info("speedtest_server", "Server used for the speedtest")
        self.ping = Gauge(
            "speedtest_ping_latency_milliseconds",
            "Speedtest ping in ms",
        )
        self.jitter = Gauge(
            "speedtest_jitter_latency_milliseconds",
            "Speedtest jitter in ms",
        )
        self.download_speed = Gauge(
            "speedtest_download_bits_per_second",
            "Measured download speed in bit/s",
        )
        self.upload_speed = Gauge(
            "speedtest_upload_bits_per_second",
            "Measured upload speed in bit/s",
        )
        self.up = Gauge("speedtest_up", "Speedtest status (via scrape)")
        self.cache_until = datetime.datetime.fromtimestamp(0)
        self.cache_secs = datetime.timedelta(seconds=cache_secs)

    @property
    def expired(self) -> bool:
        """Determine whether or not the cache has expired."""
        return datetime.datetime.now() > self.cache_until

    def update(self, result: TestResult) -> None:
        """Update the metrics and set the cache."""
        self.server.info(
            {
                "server_location_city": result.server_city,
                "server_location_region": result.server_region,
            }
        )
        self.jitter.set(result.jitter)
        self.ping.set(result.ping)
        self.download_speed.set(result.download_bps)
        self.upload_speed.set(result.upload_bps)
        self.up.set(result.status)
        self.cache_until = datetime.datetime.now() + self.cache_secs


def megabits_to_bits(megabits: float) -> int:
    """
    Convert Mbit/s to bit/s.

    NOTE: This truncates, because fractional bits would constitute a logic
    error.
    """
    return int(megabits * (10**6))
