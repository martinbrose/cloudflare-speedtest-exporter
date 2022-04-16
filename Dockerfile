FROM python:3.10.4-slim-bullseye

# Create user
RUN useradd speedtest

WORKDIR /app
COPY src/requirements.txt .

# Install required modules
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf \
     /tmp/* \
     /app/requirements

COPY src/. .

USER speedtest

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9799}/
