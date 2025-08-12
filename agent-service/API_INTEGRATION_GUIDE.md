# Agent API Integration Guide

## Overview

The agent now supports two powerful capabilities:

1. **Vector Database Queries** - Answer questions by retrieving relevant information
2. **External API Calls** - Perform actions like booking appointments, updating CRM, etc.

## 🔍 Vector Database Integration

### Purpose

The agent can query a vector database to answer specific questions about:

- Product information
- Company policies
- Procedures and processes
- FAQ responses
- Industry-specific knowledge

### How It Works

When a caller asks a question, the agent:

1. Identifies if it's an information request
2. Sends the query to the vector database with context
3. Receives relevant information
4. Formats and delivers the response naturally

### Example Usage

```python
# Customer asks: "What's your return policy?"
# Agent internally calls:
response = await query_user_information(user_id, "What's your return policy?")
# Agent responds with formatted policy information
```

### Configuration

Set up your vector database endpoint in `.env`:

```
VECTOR_DB_URL=https://api.your-vector-db.com/query
VECTOR_DB_API_KEY=your_api_key
```

## 🚀 External API Capabilities

### 1. Appointment Booking

**Check Availability:**

```python
result = await agent.check_availability("2025-08-15", "consultation")
# Returns available time slots for the date
```

**Book Appointment:**

```python
appointment_details = {
    "customer_name": "John Doe",
    "phone_number": "+1234567890",
    "preferred_date": "2025-08-15",
    "preferred_time": "14:00",
    "service_type": "consultation"
}
result = await agent.book_appointment(appointment_details)
```

### 2. CRM Integration

**Update Customer Record:**

```python
additional_info = {
    "phone_number": "+1234567890",
    "email": "john@example.com",
    "lead_score": 85,
    "stage": "qualified"
}
result = await agent.update_customer_record(additional_info)
```

### 3. Knowledge Base Queries

**Query Information:**

```python
response = await agent.query_knowledge_base("How do I reset my password?")
# Returns formatted response from vector database
```

## 📋 Business-Specific Implementations

### Sales Agent (+15551234567)

- **Queries**: Company information, pricing, product features
- **Actions**: Schedule demos, update lead scores, send follow-ups
- **Context**: Uses conversation stage and client info for personalized responses

### Restaurant Agent (+15559876543)

- **Queries**: Menu items, hours, special events
- **Actions**: Check table availability, book reservations, dietary restrictions
- **Context**: Party size, date preferences, special requests

### Social Housing Agent (+33644644937)

- **Queries**: Eligibility requirements, application process, document needs
- **Actions**: Schedule consultations, update application status
- **Context**: Housing situation, family size, income level

### AI Assistant (+15559999999)

- **Queries**: General business information, services, policies
- **Actions**: Multi-purpose booking, information retrieval, task execution
- **Context**: Adaptive based on customer needs

## 🔧 Implementation Details

### Agent Methods

Each agent instance now has these methods:

```python
# Information retrieval
async def query_knowledge_base(self, query: str) -> str

# Appointment management
async def book_appointment(self, appointment_details: Dict[str, Any]) -> Dict[str, Any]
async def check_availability(self, date: str, service_type: str = None) -> Dict[str, Any]

# CRM operations
async def update_customer_record(self, additional_info: Dict[str, Any] = None) -> Dict[str, Any]
```

### Context Integration

The system automatically includes conversation context in API calls:

- Business type
- Current conversation stage
- Collected client information
- User session details

### Error Handling

All API calls include comprehensive error handling:

- Timeout management (30-second timeout)
- Graceful fallbacks for API failures
- User-friendly error messages
- Detailed logging for debugging

## 📊 Response Formats

### Vector Database Response

```json
{
    "success": true,
    "query": "What's your return policy?",
    "results": [...],
    "confidence": 0.85,
    "sources": [...]
}
```

### Appointment Booking Response

```json
{
  "success": true,
  "confirmation_id": "APT-2025-001",
  "appointment_date": "2025-08-15",
  "appointment_time": "14:00",
  "message": "Appointment successfully booked!"
}
```

### CRM Update Response

```json
{
  "success": true,
  "contact_id": "CRM-12345",
  "lead_score": 85,
  "message": "Contact updated successfully"
}
```

## 🚀 Getting Started

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and configure your API endpoints:

```bash
cp .env.example .env
# Edit .env with your actual API endpoints and keys
```

### 2. Set Up Vector Database

Ensure your vector database accepts POST requests with this format:

```json
{
    "query": "user question",
    "context": {
        "business_type": "sales",
        "conversation_stage": "discovery",
        "client_info": {...}
    },
    "max_results": 5,
    "threshold": 0.7
}
```

### 3. Configure Business Logic

Update phone number configurations in `utils/database.py` to enable API features for specific numbers.

### 4. Test Integration

Use the AI Assistant configuration (+15559999999) to test all capabilities:

- Ask questions to test vector database queries
- Request appointments to test booking system
- Provide contact info to test CRM integration

## 🎯 Best Practices

### Vector Database Queries

- Keep queries focused and specific
- Include relevant context for better results
- Limit response length for conversational flow
- Handle cases where no results are found

### API Error Handling

- Always provide fallback responses
- Log errors for debugging but don't expose technical details to users
- Implement retry logic for transient failures
- Use timeouts to prevent hanging calls

### Context Management

- Pass relevant conversation context to improve API responses
- Update client information throughout the conversation
- Use business type to customize API behavior
- Maintain conversation flow even when APIs fail

This integration makes your agent significantly more powerful and capable of handling complex, real-world business scenarios!
