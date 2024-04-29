"""cfspeedtest exporter for Prometheus."""

import datetime
import json
import logging
import os
import sys
from collections.abc import Callable
from shutil import which
from subprocess import CalledProcessError, TimeoutExpired, check_output
from typing import NamedTuple

# TODO: determine viability of replacing flask / waitress
# with prometheus_client.start_wsgi_server - would reduce build size
from flask import Flask
from prometheus_client import Gauge, Info, make_wsgi_app
from waitress import serve


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


class Speedtest:
    """Runner class for cfspeedtest."""

    def __init__(
        self, cache_secs: int, timeout: int, cf_bin: str | None = None
    ) -> None:
        """Instantiate the runner."""
        self.metrics = Metrics(cache_secs)
        self.timeout = timeout
        self.cmd = [cf_bin or self._get_bin(), "--json"]

    def run(self) -> TestResult:
        """Run the speedtest."""
        try:
            output = check_output(self.cmd, timeout=self.timeout).decode()
        except CalledProcessError:
            logging.exception("cfspeedtest CLI failed.")
            return TestResult()
        except TimeoutExpired:
            logging.error("cfspeedtest CLI timed out and was stopped.")
            return TestResult()

        try:
            data = json.loads(output)
        except ValueError:
            logging.error(
                "cfspeedtest CLI did not return JSON. Received:\n%s", output
            )
            return TestResult()

        if "error" in data:
            # Socket error
            logging.error("Something went wrong.\nError: %s", data["error"])
            return TestResult()
        # TODO: is there a better way to test if data is valid?
        if "version" not in data:
            return TestResult()

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

    @classmethod
    def _get_bin(cls) -> str | None:
        """
        Check for the presence of cfspeedtest.

        This returns its path, or exits if it could not be found.
        """
        if (bin_loc := which("cfspeedtest")) is not None:
            return bin_loc
        logging.error(
            "Cloudflare-Speedtest CLI binary not found.\n"
            "Please install it by running 'pip install cloudflarepycli'\n"
            "https://pypi.org/project/cloudflarepycli/"
        )
        sys.exit(1)


app = Flask("Cloudflare-Speedtest-Exporter")
runner = Speedtest(
    int(os.environ.get("SPEEDTEST_CACHE_FOR", "90")),
    int(os.environ.get("SPEEDTEST_TIMEOUT", "90")),
)


@app.route("/metrics")
def update_results() -> Callable:
    """Update Prometheus metrics."""
    if datetime.datetime.now() <= runner.metrics.cache_until:
        return make_wsgi_app()

    result = runner.run()
    runner.metrics.update(result)
    logging.info(result)

    return make_wsgi_app()


@app.route("/")
def main_page() -> str:
    """Build the main webpage."""
    return (
        "<h1>Welcome to Cloudflare-Speedtest-Exporter.</h1>"
        + "Click <a href='/metrics'>here</a> to see metrics."
    )


if __name__ == "__main__":
    logging.basicConfig(
        encoding="utf-8",
        level=logging.DEBUG,
        format="level=%(levelname)s datetime=%(asctime)s %(message)s",
    )

    logging.getLogger("waitress").disabled = True

    PORT = int(os.getenv("SPEEDTEST_PORT", "9798"))
    logging.info(
        "Starting Cloudflare-Speedtest-Exporter on http://localhost:%s",
        PORT,
    )
    serve(app, host="0.0.0.0", port=PORT)
