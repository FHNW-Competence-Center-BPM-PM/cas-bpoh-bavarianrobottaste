FROM python:3.13-alpine

WORKDIR /app

COPY . /app

EXPOSE 8080

CMD ["python", "server.py"]
