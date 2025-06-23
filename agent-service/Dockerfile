FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set longer timeout for Hugging Face downloads
ENV HF_HUB_DOWNLOAD_TIMEOUT=120

RUN python agent.py download-files

RUN chmod +x start_agent_service.sh

CMD ["./start_agent_service.sh"]