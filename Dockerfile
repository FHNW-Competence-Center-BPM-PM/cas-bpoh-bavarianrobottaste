FROM python:3.13-alpine

WORKDIR /app

RUN pip install --no-cache-dir qrcode

COPY . /app

EXPOSE 8080

CMD ["python", "server.py"]
