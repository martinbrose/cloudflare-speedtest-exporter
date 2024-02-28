import datetime
import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable
from shutil import which

from flask import Flask
from prometheus_client import Gauge, Info, make_wsgi_app
from waitress import serve

app = Flask("Cloudflare-Speedtest-Exporter")  # Create flask app

# Setup logging values
logging.basicConfig(
    encoding="utf-8",
    level=logging.DEBUG,
    format="level=%(levelname)s datetime=%(asctime)s %(message)s",
)

# Disable Waitress Logs
logging.getLogger("waitress").disabled = True

# Metrics
server = Info("speedtest_server", "Server used for the speedtest")
ping = Gauge("speedtest_ping_latency_milliseconds", "Speedtest ping in ms")
jitter = Gauge(
    "speedtest_jitter_latency_milliseconds", "Speedtest jitter in ms"
)
download_speed = Gauge(
    "speedtest_download_bits_per_second",
    "Measured download speed in bit/s",
)
upload_speed = Gauge(
    "speedtest_upload_bits_per_second",
    "Measured upload speed in bit/s",
)
up = Gauge("speedtest_up", "Speedtest status (via scrape)")

# Cache duration
CACHE_SECS = datetime.timedelta(int(os.environ.get("SPEEDTEST_CACHE_FOR", 0)))
cache_until = datetime.datetime.fromtimestamp(0)

# Test running constants
TEST_CMD = ["cfspeedtest", "--json"]
type TestResult = tuple[str, str, float, float, float, float, float, float, int]
NULL_RESULT: TestResult = ("", "", 0, 0, 0, 0, 0, 0, 0)


def bits_to_megabits(bits_per_sec: float) -> str:
    megabits = round(bits_per_sec * (10**-6), 2)
    return str(megabits) + "Mbps"


def megabits_to_bits(megabits: float) -> str:
    bits_per_sec = megabits * (10**6)
    return str(bits_per_sec)


def run_test() -> TestResult:
    timeout = int(os.environ.get("SPEEDTEST_TIMEOUT", "90"))

    try:
        output = (
            subprocess.check_output(TEST_CMD, timeout=timeout).decode().strip()
        )
    except subprocess.CalledProcessError:
        logging.exception("cfspeedtest CLI failed.")
        return NULL_RESULT
    except subprocess.TimeoutExpired:
        logging.error("cfspeedtest CLI timed out and was stopped.")
        return NULL_RESULT

    try:
        data = json.loads(output)
    except ValueError:
        logging.error(
            "cfspeedtest CLI did not produce valid JSON. Received:\n%s", output
        )
        return NULL_RESULT

    if "error" in data:
        # Socket error
        logging.error("Something went wrong.\nError: %s", data["error"])
        return NULL_RESULT
    # TODO: is there a better way to test if data is valid?
    if "version" not in data:
        return NULL_RESULT

    return (
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
    global cache_until

    if datetime.datetime.now() <= cache_until:
        return make_wsgi_app()

    (
        r_server_city,
        r_server_region,
        r_ping,
        r_jitter,
        r_download_mbps,
        r_download,
        r_upload_mbps,
        r_upload,
        r_status,
    ) = run_test()
    server.info(
        {
            "server_location_city": r_server_city,
            "server_location_region": r_server_region,
        }
    )
    jitter.set(r_jitter)
    ping.set(r_ping)
    download_speed.set(r_download)
    upload_speed.set(r_upload)
    up.set(r_status)
    logging.info(
        "Server City=%s "
        "Server Region=%s "
        "Jitter=%sms "
        "Ping=%sms "
        "Download=%sMb/s "
        "Upload=%sMb/s",
        r_server_city,
        r_server_region,
        r_jitter,
        r_ping,
        r_download_mbps,
        r_upload_mbps,
    )

    cache_until = datetime.datetime.now() + CACHE_SECS
    return make_wsgi_app()


@app.route("/")
def main_page() -> str:
    return (
        "<h1>Welcome to Cloudflare-Speedtest-Exporter.</h1>"
        + "Click <a href='/metrics'>here</a> to see metrics."
    )


def check_cfspeedtest() -> None:
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
