"""cfspeedtest exporter for Prometheus."""

import datetime
import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from shutil import which
from typing import NamedTuple, Self

from flask import Flask
from prometheus_client import Gauge, Info, make_wsgi_app
from waitress import serve

app = Flask("Cloudflare-Speedtest-Exporter")

# Setup logging with a specific format and level
logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    format="level=%(levelname)s datetime=%(asctime)s %(message)s",
)

# Disable Waitress Logs
logging.getLogger("waitress").disabled = True


class TestResult(NamedTuple):
    """Result of a speedtest."""

    server_city: str
    server_region: str
    ping: float
    jitter: float
    download_mbps: float
    download_bps: int
    upload_mbps: float
    upload_bps: int
    status: int

    @property
    def NULL() -> Self:
        """
        Return a null result.
        
        This could be done with defaults, but mandating the deliberate
        construction of this reduces the likelihood of errors."""
        return TestResult("", "", 0, 0, 0, 0, 0, 0, 0)

    def __repr__(self) -> str:
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
    def __init__(self, cache_secs: int):
        self.server = Info("speedtest_server", "Server used for the speedtest")
        self.ping = Gauge("speedtest_ping_latency_milliseconds", "Speedtest ping in ms")
        self.jitter = Gauge("speedtest_jitter_latency_milliseconds", "Speedtest jitter in ms")
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

    def update(self, result: TestResult):
        self.server.info({
            "server_location_city": result.server_city,
            "server_location_region": result.server_region,
        })
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


metrics = Metrics(int(os.environ.get("SPEEDTEST_CACHE_FOR", "90")))
TEST_CMD = ["cfspeedtest", "--json"]

def run_test() -> TestResult:
    """Run the speedtest and parse the results."""
    timeout = int(os.environ.get("SPEEDTEST_TIMEOUT", "90"))

    try:
        output = (
            subprocess.check_output(TEST_CMD, timeout=timeout).decode().strip()
        )
    except subprocess.CalledProcessError:
        logging.exception("cfspeedtest CLI failed.")
        return TestResult.NULL
    except subprocess.TimeoutExpired:
        logging.error("cfspeedtest CLI timed out and was stopped.")
        return TestResult.NULL

    try:
        data = json.loads(output)
    except ValueError:
        logging.error(
            "cfspeedtest CLI did not produce valid JSON. Received:\n%s", output
        )
        return TestResult.NULL

    if "error" in data:
        # Socket error
        logging.error("Something went wrong.\nError: %s", data["error"])
        return TestResult.NULL
    # TODO: is there a better way to test if data is valid?
    if "version" not in data:
        return TestResult.NULL

    return TestResult(
        data["test_location_city"]["value"],
        data["test_location_region"]["value"],
        data["latency_ms"]["value"],
        data["Jitter_ms"]["value"],
        download_mbps := data["90th_percentile_download_speed"]["value"],
        megabits_to_bits(download_mbps),
        upload_mbps := data["90th_percentile_upload_speed"]["value"],
        megabits_to_bits(upload_mbps),
        1,
    )


@app.route("/metrics")
def update_results() -> Callable:
    """Update Prometheus metrics."""
    if datetime.datetime.now() <= metrics.cache_until:
        return make_wsgi_app()

    result = run_test()
    metrics.update(result)
    logging.info(result)

    return make_wsgi_app()


@app.route("/")
def main_page() -> str:
    """Build the main webpage."""
    return (
        "<h1>Welcome to Cloudflare-Speedtest-Exporter.</h1>"
        + "Click <a href='/metrics'>here</a> to see metrics."
    )


def check_cfspeedtest() -> None:
    """Check for the presence of cfspeedtest and exit if it is not found."""
    if which("cfspeedtest") is None:
        logging.error(
            "Cloudflare-Speedtest CLI binary not found.\n"
            "Please install it by running 'pip install cloudflarepycli'\n"
            "https://pypi.org/project/cloudflarepycli/"
        )
        sys.exit(1)


if __name__ == "__main__":
    check_cfspeedtest()
    PORT = int(os.getenv("SPEEDTEST_PORT", "9798"))
    logging.info(
        "Starting Cloudflare-Speedtest-Exporter on http://localhost:%s",
        PORT,
    )
    serve(app, host="0.0.0.0", port=PORT)
