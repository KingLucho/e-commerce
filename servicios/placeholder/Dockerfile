FROM python:3.12-alpine

WORKDIR /app
COPY health_server.py ./health_server.py

USER nobody
EXPOSE 8080
CMD ["python", "-u", "health_server.py"]
