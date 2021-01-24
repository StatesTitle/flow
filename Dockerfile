FROM python:3.9.1-slim

RUN apt-get update && apt-get install --yes graphviz

RUN mkdir /app
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py ./
CMD ["gunicorn", "web:app"]