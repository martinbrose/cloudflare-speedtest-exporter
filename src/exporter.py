"""cfspeedtest exporter for Prometheus."""

import json
import logging
import os
import sys
from shutil import which
from subprocess import CalledProcessError, TimeoutExpired, check_output
from threading import Thread
from wsgiref.simple_server import WSGIServer
from wsgiref.types import StartResponse, WSGIEnvironment

from prometheus_client import make_wsgi_app, start_wsgi_server
from utils import Metrics, TestResult, megabits_to_bits


class Speedtest:
    """Runner class for cfspeedtest and the metrics endpoint."""

    def __init__(
        self,
        cache_secs: int,
        timeout: int,
        port: int,
        cf_bin: str | None = None,
    ) -> None:
        """Instantiate the runner."""
        self.metrics = Metrics(cache_secs)
        self.timeout = timeout
        self.server_port = port
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

    def wsgi_app(
        self, environ: WSGIEnvironment, start_resp: StartResponse
    ) -> list:
        """WSGI endpoint to fetch cached metrics or run a new speedtest."""
        if environ["PATH_INFO"] != "/metrics":
            start_resp("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [
                b"<h1>Welcome to Cloudflare-Speedtest-Exporter</h1>",
                b"Click <a href='/metrics'>here</a> to see metrics.",
            ]
        if not self.metrics.expired:
            logging.debug("Metrics requested - returning from cache hit.")
            return make_wsgi_app()(environ, start_resp)

        logging.debug("Metrics requested - cache outdated, running speedtest.")
        result = self.run()
        self.metrics.update(result)
        logging.info(result)

        return make_wsgi_app()(environ, start_resp)

    def start_server(self) -> tuple[WSGIServer, Thread]:
        """Start a WSGI server for the endpoint."""
        logging.info(
            "Starting Cloudflare-Speedtest-Exporter on http://localhost:%s",
            self.server_port,
        )

        server, thread = start_wsgi_server(self.server_port, "0.0.0.0")
        server.set_app(self.wsgi_app)
        return (server, thread)

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


if __name__ == "__main__":
    logging.basicConfig(
        encoding="utf-8",
        level=logging.DEBUG,
        datefmt="%F %T",
        format="[%(levelname)-8s] (%(asctime)s): %(message)s",
    )

    runner = Speedtest(
        int(os.environ.get("SPEEDTEST_CACHE_FOR", "90")),
        int(os.environ.get("SPEEDTEST_TIMEOUT", "90")),
        int(os.getenv("SPEEDTEST_PORT", "9798")),
    )
    server, thread = runner.start_server()

    try:
        thread.join()
    except KeyboardInterrupt:
        logging.info("Exiting!")
        server.shutdown()
        thread.join()
