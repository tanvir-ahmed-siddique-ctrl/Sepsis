FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY edge /app/edge

RUN useradd --system --uid 10001 --create-home edge \
    && mkdir -p /var/lib/predictrx-edge \
    && chown edge:edge /var/lib/predictrx-edge

USER edge
EXPOSE 2575 8081
VOLUME ["/var/lib/predictrx-edge"]

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health', timeout=2)"

CMD ["python", "-m", "edge.service"]

