FROM python:3.12.1-alpine3.18

# Create user
RUN adduser -D speedtest

WORKDIR /app

COPY src/. .

RUN pip install --no-cache-dir -r requirements.txt \
    && find /usr/local/lib/python3.12 -name "*.pyc" -type f -delete

USER speedtest

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9798}/
