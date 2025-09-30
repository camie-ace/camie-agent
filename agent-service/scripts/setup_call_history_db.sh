#!/bin/bash

# Setup script for call history with database storage

# Determine the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"

# Go to the agent directory
cd "$AGENT_DIR"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Function to create a .env file with the given variables
create_env_file() {
    echo "Creating .env file..."
    cat > .env << EOL
# Call History Storage Configuration
CALL_HISTORY_STORAGE=mongodb
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=agent_service
MONGODB_COLLECTION=call_history

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
CALL_HISTORY_API_KEY=your_secure_api_key_here
EOL
    echo ".env file created successfully."
}

# Function to start MongoDB
start_mongodb() {
    echo "Starting MongoDB Docker container..."
    docker run -d --name mongodb -p 27017:27017 mongo:latest
    echo "MongoDB started successfully."
}

# Function to install required packages
install_packages() {
    echo "Installing required packages..."
    pip install fastapi uvicorn motor pymongo redis
    echo "Packages installed successfully."
}

# Main menu
echo "Call History Database Setup"
echo "=========================="
echo "This script will help you set up a database for call history storage."
echo ""
echo "Choose an option:"
echo "1. Setup MongoDB (using Docker)"
echo "2. Setup Redis (using Docker)"
echo "3. Install required packages"
echo "4. Create .env file"
echo "5. Start API server"
echo "6. Exit"
echo ""

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo "Setting up MongoDB..."
        start_mongodb
        create_env_file
        ;;
    2)
        echo "Setting up Redis..."
        docker run -d --name redis -p 6379:6379 redis:latest
        # Update .env file for Redis
        cat > .env << EOL
# Call History Storage Configuration
CALL_HISTORY_STORAGE=redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
CALL_HISTORY_API_KEY=your_secure_api_key_here
EOL
        echo "Redis setup complete."
        ;;
    3)
        install_packages
        ;;
    4)
        create_env_file
        ;;
    5)
        echo "Starting API server..."
        python -m api.main
        ;;
    6)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Setup complete. You can now use the call history with database storage."
echo "To start the API server, run: python -m api.main"
echo "To test the API, visit: http://localhost:8080/docs"