# Import necessary libraries
import datetime
import json
import logging
import os
import subprocess
import socket
from dataclasses import dataclass, field
from shutil import which
from typing import Optional

from flask import Flask
from prometheus_client import make_wsgi_app, Gauge, Info
from waitress import serve

from utils import megabits_to_bits, is_json

# Create a Flask application
app = Flask("Cloudflare-Speedtest-Exporter")

# Setup logging with a specific format and level
format_string = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG,
                    format=format_string)

# Disable Waitress Logs
log = logging.getLogger('waitress')
log.disabled = True


@dataclass
class TestResult:
    """
    Represents the result of a speed test.

    Attributes:
        server_city (Optional[str]): The city of the server used for the speed test.
        server_region (Optional[str]): The region of the server used for the speed test.
        ping (Optional[float]): The ping time in milliseconds.
        jitter (Optional[float]): The jitter time in milliseconds.
        download_mbps (Optional[float]): The download speed in megabits per second.
        download (Optional[float]): The download speed in bits per second.
        upload_mbps (Optional[float]): The upload speed in megabits per second.
        upload (Optional[float]): The upload speed in bits per second.
        status (Optional[int]): The status of the speed test.

    Methods:
        run_test(): Runs the speed test.
    """

    server_city: Optional[str] = field(default="")
    server_region: Optional[str] = field(default="")
    ping: Optional[float] = field(default=0.0)
    jitter: Optional[float] = field(default=0.0)
    download_mbps: Optional[float] = field(default=0.0)
    download: Optional[float] = field(default=0.0)
    upload_mbps: Optional[float] = field(default=0.0)
    upload: Optional[float] = field(default=0.0)
    status: Optional[int] = field(default=0)

    def run_test(self):
        """
        Runs the speed test and parses the results.

        Returns:
            None
        """
        output = self._execute_speedtest()
        if output:
            self._parse_results(output)

    def _execute_speedtest(self):
        timeout = int(os.environ.get('SPEEDTEST_TIMEOUT', 90))
        cmd = ["cfspeedtest", "--json"]

        try:
            socket.create_connection(("speed.cloudflare.com", 80))
        except OSError:
            logging.error('No internet connection. Please check your network settings.')
            return None

        try:
            output = subprocess.check_output(cmd, timeout=timeout)
            return output.decode().rsplit('}', 1)[0] + "}"
        except subprocess.CalledProcessError as e:
            output = e.output
            if not is_json(output) and len(output) > 0:
                logging.error('CFSpeedtest CLI Error occurred that was not in JSON format')
            return None
        except subprocess.TimeoutExpired:
            logging.error('CFSpeedtest CLI process took too long to complete and was killed.')
            return None

    def _parse_results(self, output):
        data = json.loads(output)
        if "error" in data:
            print('Something went wrong')
            print(data['error'])
            return
        if "version" in data:
            self.server_city = data['test_location_city']['value']
            self.server_region = data['test_location_region']['value']
            self.ping = data['latency_ms']['value']
            self.jitter = data['Jitter_ms']['value']
            self.download_mbps = data['90th_percentile_download_speed']['value']
            self.download = megabits_to_bits(self.download_mbps)
            self.upload_mbps = data['90th_percentile_upload_speed']['value']
            self.upload = megabits_to_bits(self.upload_mbps)
            self.status = 1


class SpeedTest:
    """
    Class representing a speed test.

    Attributes:
        cache_seconds (int): The number of seconds to cache the speed test results.
        cache_until (datetime.datetime): The datetime until which the cache is valid.
    """

    def __init__(self):
        self.cache_seconds = int(os.environ.get('SPEEDTEST_CACHE_FOR', 0))
        self.cache_until = datetime.datetime.fromtimestamp(0)

    def update_cache(self):
        """
        Updates the cache by setting the cache_until attribute to the current time plus the cache_seconds.
        """
        self.cache_until = datetime.datetime.now() + datetime.timedelta(seconds=self.cache_seconds)

    def is_cache_expired(self):
        """
        Checks if the cache has expired.

        Returns:
            bool: True if the cache has expired, False otherwise.
        """
        return datetime.datetime.now() > self.cache_until

    def run_speedtest(self):
        """
        Runs the speed test and returns the result if the cache has expired.

        Returns:
            TestResult or None: The speed test result if the cache has expired, None otherwise.
        """
        if self.is_cache_expired():
            result = TestResult()
            result.run_test()
            logging.info(f"Server City={result.server_city} Server Region={result.server_region} "
                         f"Jitter={result.jitter}ms Ping={result.ping}ms "
                         f"Download={result.download_mbps}Mbps Upload={result.upload_mbps}Mbps")
            self.update_cache()
            return result
        return None


class Metrics:
    """
    Class representing the metrics for the speedtest exporter.

    Attributes:
        server (Info): Information about the server used for the speedtest.
        jitter (Gauge): Speedtest jitter in milliseconds.
        ping (Gauge): Speedtest ping in milliseconds.
        download_speed (Gauge): Measured download speed in bits per second.
        upload_speed (Gauge): Measured upload speed in bits per second.
        up (Gauge): Speedtest status (via scrape).
    """

    def __init__(self):
        self.server = Info(
            'speedtest_server',
            'Information about the server used for the speedtest'
        )
        self.jitter = Gauge(
            'speedtest_jitter_latency_milliseconds',
            'Speedtest jitter in ms'
        )
        self.ping = Gauge(
            'speedtest_ping_latency_milliseconds',
            'Speedtest ping in ms'
        )
        self.download_speed = Gauge(
            'speedtest_download_bits_per_second',
            'Measured download speed in bit/s'
        )
        self.upload_speed = Gauge(
            'speedtest_upload_bits_per_second',
            'Measured upload speed in bit/s'
        )
        self.up = Gauge(
            'speedtest_up',
            'Speedtest status (via scrape)'
        )

    def update_metrics(self, result):
        """
        Update the metrics with the given speedtest result.

        Args:
            result: The speedtest result object containing the metrics to update.
        """
        self.server.info({
            'server_location_city': str(result.server_city),
            'server_location_region': str(result.server_region)
        })
        self.jitter.set(result.jitter)
        self.ping.set(result.ping)
        self.download_speed.set(result.download)
        self.upload_speed.set(result.upload)
        self.up.set(result.status)


# Create instances
speedtest = SpeedTest()
metrics = Metrics()


@app.route("/metrics")
def update_results():
    result = speedtest.run_speedtest()
    if result is not None:
        metrics.update_metrics(result)
    return make_wsgi_app()


# Define route for the main page
@app.route("/")
def main_page():
    return ("<h1>Welcome to Cloudflare-Speedtest-Exporter.</h1>" +
            "Click <a href='/metrics'>here</a> to see metrics.")


# Define function to check for the presence of the cfspeedtest binary
def check_for_binary():
    if which("cfspeedtest") is None:
        logging.error("Cloudflare-Speedtest CLI binary not found.\n" +
                      "Please install it by running\n" +
                      "'pip install cloudflarepycli'\n" +
                      "https://pypi.org/project/cloudflarepycli/")
        exit(1)


# Start the application if this script is run directly
if __name__ == '__main__':
    check_for_binary()
    PORT = os.getenv('SPEEDTEST_PORT', 9798)
    logging.info("Starting Cloudflare-Speedtest-Exporter on http://localhost:" +
                 str(PORT))
    serve(app, host='0.0.0.0', port=PORT)
