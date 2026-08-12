FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY api ./api
COPY simulation ./simulation
COPY models ./models
COPY analysis ./analysis
COPY data ./data
COPY research ./research
COPY visualizations ./visualizations

EXPOSE 7860
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1