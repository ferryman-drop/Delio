FROM python:3.11-slim
WORKDIR /app

# Install system deps for some packages (if needed)
# Install system deps including ffmpeg for audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m appuser

COPY . .

# Set ownership and permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

ENV PYTHONUNBUFFERED=1

VOLUME ["/app/data"]

CMD ["python", "main.py"]
