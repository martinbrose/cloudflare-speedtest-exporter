"""cfspeedtest exporter for Prometheus."""

import logging
import os
from threading import Thread
from wsgiref.simple_server import WSGIServer
from wsgiref.types import StartResponse, WSGIEnvironment

from cfspeedtest import CloudflareSpeedtest
from prometheus_client import make_wsgi_app, start_wsgi_server
from requests import ConnectionError, Timeout
from utils import Metrics, TestResult, bits_to_megabits


class Speedtest:
    """Runner class for cfspeedtest and the metrics endpoint."""

    def __init__(
        self,
        cache_secs: int,
        timeout: tuple[float, float] | float,
        port: int,
    ) -> None:
        """Instantiate the runner."""
        self.metrics = Metrics(cache_secs)
        self.server_port = port
        self.suite = CloudflareSpeedtest(timeout=timeout)

    def run(self) -> TestResult:
        """Run the speedtest."""
        try:
            results = self.suite.run_all()
        except ConnectionError:
            logging.error("cfspeedtest could not connect.")
            return TestResult()
        except Timeout:
            logging.error("A connection timed out and was stopped.")
            return TestResult()

        return TestResult(
            results["meta"]["location_city"].value,
            results["meta"]["location_region"].value,
            results["tests"]["latency"].value,
            results["tests"]["jitter"].value,
            down_bps := results["tests"]["90th_percentile_down_bps"].value,
            bits_to_megabits(down_bps),
            up_bps := results["tests"]["90th_percentile_up_bps"].value,
            bits_to_megabits(up_bps),
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
