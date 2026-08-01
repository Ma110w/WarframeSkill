FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTMCP_STATELESS_HTTP=true \
    FASTMCP_JSON_RESPONSE=true \
    FASTMCP_SHOW_SERVER_BANNER=false \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn

COPY clients.py overframe.py platinum.py server.py http_app.py ./

EXPOSE 8080

CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "8080"]
