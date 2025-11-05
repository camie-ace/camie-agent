FROM python:3.11-slim

# Install necessary utilities to fetch the uv binary
# We use a single RUN command to minimize layers
RUN apt-get update \
    && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (the Rust-based package manager)
# The output is piped to sh to execute the install script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add the directory where uv is installed to the PATH
# This path is where the install script places the binary
ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .

# Use uv to install dependencies
# --system: tells uv to install into the base Python environment (not a venv)
# --no-cache-dir: similar to pip's flag, saves space in the Docker image
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

# Set longer timeout for Hugging Face downloads
ENV HF_HUB_DOWNLOAD_TIMEOUT=120

RUN python agent.py download-files

RUN chmod +x start_agent_service.sh

CMD ["./start_agent_service.sh"]