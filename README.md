# Cloudflare Speedtest Exporter

The **Cloudflare Speedtest Exporter** is a simple and efficient **Prometheus** exporter written in **Python**.
It utilizes the [**CloudFlare** Python CLI by Tom Evslin](https://pypi.org/project/cloudflarepycli) to provide valuable network speed metrics in Prometheus format.
The exporter reports the 90th percentile speed data, which aligns with the Cloudflare site's reported values.
It is based on [Miguel de Carvalho's Ookla speedtest exporter](https://github.com/MiguelNdeCarvalho/speedtest-exporter).

Published on [Docker Hub here](https://hub.docker.com/r/redorbluepill/cloudflare-speedtest-exporter).
## Overview

This exporter offers a seamless way to monitor network performance by reporting key metrics such as ping latency, jitter, download speed, and upload speed.
The tool is designed to be easily integrated with Prometheus, enabling you to visualize and set up alerts based on these metrics.
The exporter's structure follows best practices, making it efficient and lightweight.

## Usage

1. **Running the Exporter**: The exporter is configured to work with Docker containers.
By building the provided Docker image, you can deploy the exporter with ease.
2. **Metrics**: The exporter provides the following metrics:
    - Ping Latency
    - Jitter
    - Download Speed
    - Upload Speed
    - Server Location (city and region)
3. **Prometheus Integration**: The exporter exposes metrics through a Prometheus-compatible endpoint.
You can configure Prometheus to scrape these metrics and store them for analysis and visualization.

## Docker Hub

You can find the published Docker image on Docker Hub [here](https://hub.docker.com/r/redorbluepill/cloudflare-speedtest-exporter).

## Get Started

1. Clone this repository.
2. Customize the exporter to fit your requirements.
3. Build the Docker image using the provided Dockerfile.
4. Deploy the Docker container and start gathering network speed metrics.

## Acknowledgments and Thank You

This project builds upon the valuable work of others and their contributions:

- [Miguel de Carvalho](https://github.com/MiguelNdeCarvalho): The project draws main inspiration from Miguel de Carvalho's Ookla speedtest exporter.
- [Tom Evslin](https://github.com/tevslin): The CloudFlare Python CLI by Tom Evslin serves as a crucial component for fetching network speed data.

## License

This project is licensed under the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.en.html).

For more details, refer to the [License file](./LICENSE).
