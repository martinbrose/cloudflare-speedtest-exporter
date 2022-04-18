FROM python:3.10-slim

# Create user
RUN useradd speedtest

WORKDIR /app
COPY src/requirements.txt .

# Install required modules
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        make \
        gcc \
        dpkg-dev \
        libjpeg-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y --purge make gcc build-essential dpkg-dev libjpeg-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/local/lib/python3.10 -name "*.pyc" -type f -delete

COPY src/. .

USER speedtest

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9798}/
