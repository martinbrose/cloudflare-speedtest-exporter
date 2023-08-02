FROM python:3.11.1-alpine3.17

# Create user
RUN adduser -D speedtest

WORKDIR /app

# Install required modules
RUN apk update && \
    apk add --no-cache make=4.3-r1 build-base=0.5-r3 \
    && pip install --no-cache numpy==1.24.1 \
    && apk del make build-base \
    && rm -rf /var/cache/apk/*

COPY src/. .

RUN pip install --no-cache -r requirements.txt 
RUN find /usr/local/lib/python3.11 -name "*.pyc" -type f -delete

USER speedtest

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9798}/
