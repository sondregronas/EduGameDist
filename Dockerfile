FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV GAMES_DIR=/app/public/games
# Game files are only written to GAMES_DIR when it is a mounted volume, so they survive image updates.
ENV GAMES_MOUNT_REQUIRED=1
WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/. .
RUN mkdir -p /app/data/uploads /app/data/upload-tmp
EXPOSE 80/tcp 8081/tcp
CMD ["gunicorn", "--worker-class", "gthread", "--workers", "2", "--threads", "4", "--timeout", "0", "--bind", "0.0.0.0:80", "app:create_public_app()"]
