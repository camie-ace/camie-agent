# Call History Module

This module provides comprehensive call tracking and analytics for the LiveKit agent service.

## Key Features

1. **Call Tracking**

   - Records complete call lifecycle (start, stages, end)
   - Captures detailed metadata, metrics, and outcomes
   - Supports inbound and outbound calls

2. **Database Support**

   - Configurable storage backends:
     - JSON file storage (default, simple)
     - Redis database (high performance, easy scaling)
     - MongoDB (rich querying, enterprise-ready)

3. **API Access**

   - REST API for accessing call history data
   - Secured with API keys
   - Comprehensive endpoints for querying and reporting

4. **Analytics & Reporting**
   - Generate call summary reports
   - Export to CSV for data analysis
   - Filter by phone number, date range, business type, etc.

## Configuration

### Storage Configuration

Set the desired storage type using environment variables:

```bash
# For JSON file storage (default)
CALL_HISTORY_STORAGE=json
CALL_HISTORY_FILE=/path/to/call_records.json  # Optional, defaults to data/call_history/call_records.json

# For Redis storage
CALL_HISTORY_STORAGE=redis
REDIS_URL=redis://localhost:6379/0

# For MongoDB storage
CALL_HISTORY_STORAGE=mongodb
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=agent_service
MONGODB_COLLECTION=call_history
```

### API Configuration

```bash
# API server configuration
API_HOST=0.0.0.0
API_PORT=8080
CALL_HISTORY_API_KEY=your_secure_api_key_here
```

## Setup & Usage

### 1. Database Setup

Use the provided setup script:

```bash
# Make the script executable
chmod +x scripts/setup_call_history_db.sh

# Run the setup script
./scripts/setup_call_history_db.sh
```

### 2. Starting the API Server

```bash
# Start the API server
python -m api.main

# Or use the provided script
./scripts/start_api_server.sh
```

### 3. Accessing Call Data

#### Using the API

The API provides comprehensive access to call history data:

- `GET /api/history/calls/recent` - Get recent calls
- `GET /api/history/calls/phone/{phone_number}` - Get calls for a specific phone number
- `GET /api/history/calls/{call_id}` - Get details for a specific call
- `GET /api/history/stats` - Get call statistics
- `GET /api/history/reports/summary` - Generate a summary report
- `GET /api/history/reports/csv` - Export call history as CSV

#### Using the Report Generator

Generate reports from the command line:

```bash
# Generate a JSON report
python scripts/generate_call_report.py --format json --output reports/

# Generate a CSV report
python scripts/generate_call_report.py --format csv --output reports/calls.csv

# Filter by phone number
python scripts/generate_call_report.py --format csv --output reports/specific_calls.csv --phone "+15551234567"
```

## Example API Usage

```python
import requests

# API endpoint
BASE_URL = "http://localhost:8080/api/history"
API_KEY = "your_secure_api_key_here"

# Headers
headers = {
    "X-API-Key": API_KEY
}

# Get recent calls
response = requests.get(f"{BASE_URL}/calls/recent", headers=headers)
recent_calls = response.json()

# Get calls for a specific phone number
phone_number = "+15551234567"
response = requests.get(f"{BASE_URL}/calls/phone/{phone_number}", headers=headers)
phone_calls = response.json()

# Get call statistics
response = requests.get(f"{BASE_URL}/stats", headers=headers)
stats = response.json()

# Export as CSV
response = requests.get(f"{BASE_URL}/reports/csv", headers=headers)
with open("call_history.csv", "w") as f:
    f.write(response.text)
```
