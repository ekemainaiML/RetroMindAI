FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    freecad \
    python3 python3-pip \

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    freecad-python3 \
    RUN pip install --no-cache-dir fastapi uvicorn httpx

COPY worker.py /worker.py

EXPOSE 8100

CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8100"]
