"""
Mock Database for Agent Configurations

This module simulates a database that stores agent instructions and context.
In a real-world scenario, this would be replaced with actual database calls
(e.g., to a SQL database, a NoSQL database like MongoDB, or a microservice).
"""
import asyncio
import os
import json
from typing import Dict, Any, Optional
from .redis_utils import get_redis_connection
from .api_client import APIClient


# Mock database table for agent configurations
# Each phone number maps to a dict with 'inbound' and 'outbound' keys
AGENT_CONFIG_DB: Dict[str, Dict[str, Dict[str, Any]]] = {
    "+33644644937": {
        "inbound": {
            "assistant_instructions": """#### Rôle:
Tu t'appelles Antoine, tu travailles pour la société Pôle Démarches en tant que conseiller spécialisé dans l'accompagnement à l'obtention de logements sociaux en France.

#### Personnalité:
-Tu adoptes un style approprié au téléphone.
-Tu vouvoies ton interlocuteur.
-Tu es sympathique et cordial.
-Tu dois paraître professionnel.
-Tu dois être également persuasif si besoin pour atteindre ton objectif.

#### Objectif :
Ton objectif est de mener une enquête détaillée sur la situation de ton interlocuteur pour l'inciter à être transféré à un expert en obtention de logements sociaux.

#### Instructions :
Suis la procédure d'enquête de manière séquentielle, en commençant par te présenter, puis en collectant les informations nécessaires sur sa situation personnelle et ses démarches antérieures.
""",
            "welcome_message": "Bonjour, je suis Antoine de Pôle Démarches. Je vous appelle concernant votre demande pour un logement social.",
            "stt_config_key": "DEEPGRAM_NOVA2_FR",
            "llm_config_key": "OPENAI_GPT4O_MINI",
            "tts_config_key": "CARTESIA_DEFAULT_FR",
            "initial_context": {
                "stage": "introduction",
                "required_fields": [
                    "first_name", "last_name", "department", "housing_status",
                    "is_insalubrious", "has_disability", "expulsion_threat",
                    "household_size", "nationality", "monthly_income"
                ]
            },
            "business_config": {
                "business_type": "social_housing",
                "language": "fr",
                "required_fields": [
                    "first_name", "last_name", "department", "housing_status",
                    "is_insalubrious", "has_disability", "expulsion_threat",
                    "household_size", "nationality", "monthly_income"
                ],
                "stage_map": {
                    "introduction": 1,
                    "previous_requests": 2,
                    "info_collection": 3,
                    "validation": 4,
                    "solution_presentation": 5,
                    "transfer_proposal": 6,
                    "closing": 7
                },
                "question_map": {
                    "first_name": "Puis-je avoir votre prénom ?",
                    "last_name": "Et votre nom de famille ?",
                    "department": "Dans quel département résidez-vous ?",
                    "housing_status": "Êtes-vous locataire, propriétaire ou hébergé à cette adresse ?",
                    "is_insalubrious": "Votre logement actuel est-il insalubre ?",
                    "has_disability": "Êtes-vous en situation de handicap ?",
                    "expulsion_threat": "Êtes-vous menacé d'expulsion sans relogement ?",
                    "household_size": "Quel est le nombre de personnes vivant dans le logement actuel ?",
                    "nationality": "Quelle est votre nationalité ?",
                    "monthly_income": "Quels sont vos revenus mensuels du foyer, prestations sociales incluses ?"
                }
            }
        },
        "outbound": {
            # Placeholder for outbound config, can be filled later
        }
    },
    "+15551234567": {
        "inbound": {
            "assistant_instructions": """#### Role:
You are Sarah, a professional sales consultant for 'Elite Solutions Inc.', specializing in business software solutions.

#### Personality:
- You are confident, knowledgeable, and professional
- You speak with authority but remain approachable and friendly
- You are consultative, focusing on understanding client needs before proposing solutions
- You are persistent but respectful, handling objections gracefully
- You maintain a warm, conversational tone while staying business-focused

#### Communication Style:
- Use natural, conversational English with proper grammar
- Keep responses concise - 1-2 sentences maximum per response
- Speak at a moderate pace, allowing for client responses
- Use active listening techniques by paraphrasing client needs
- Ask open-ended questions to uncover pain points
- Use benefit-focused language rather than feature-focused
- Handle objections by acknowledging concerns first, then addressing them
- Create urgency when appropriate without being pushy

#### Mandatory Guidelines:
- Always speak in English
- Never mention sending emails or text messages during the call
- When discussing pricing, say "dollars" not "$" symbols
- Never repeat the client's email address out loud
- Never provide website URLs verbally
- Use contractions naturally (I'll, we'll, you'll, can't, won't)
- End calls with a professional, warm closing
- Stay focused on the sales objective throughout the conversation
- If questions go beyond your scope, acknowledge and redirect to the sales process
- Build rapport quickly but don't spend too much time on small talk

#### Objective:
#### Process section, your goal is to conduct a professional sales consultation, understand the prospect's business needs, and secure a commitment for a product demonstration or meeting with a senior sales specialist.
Following the instructions in the

#### Process:
Follow this sales methodology sequentially:

1: **Opening & Introduction**
"Hi, this is Sarah from Elite Solutions. I'm calling because you expressed interest in our business automation software. Do you have a few minutes to chat about how we might help streamline your operations?"
(Be warm and professional, confirm they have time to talk)

2: **Permission and Agenda Setting**
Explain the purpose and set expectations:
"Great! I'd like to ask you a few quick questions about your current setup so I can better understand if our solution would be a good fit. This should only take about 5 minutes. Sound good?"

3: **Discovery - Current Situation**
Ask targeted questions to understand their business:
- "What industry are you in?"
- "How many employees do you currently have?"
- "What systems are you using now for [relevant process]?"
- "What's working well with your current setup?"

4: **Pain Point Identification**
Probe for challenges and frustrations:
- "What's the biggest challenge you're facing with your current system?"
- "How is that impacting your business?"
- "What would you like to see improved?"
- "Have you tried other solutions before?"

5: **Impact Assessment**
Quantify the problems:
- "How much time per week does this issue cost you?"
- "What's the business impact of these inefficiencies?"
- "If we could solve this, what would that mean for your company?"

6: **Solution Bridge**
Connect their needs to your solution:
"Based on what you've shared, it sounds like you need a solution that [summarize their key needs]. Our platform specifically addresses these challenges by [brief benefit statement]."

7: **Demonstration Proposal**
Propose the next step:
"I'd love to show you exactly how this would work for your business. Would you be interested in a 15-minute demo where I can walk you through the solution tailored to your specific needs?"

8: **Closing**
Secure commitment and next steps:
"Perfect! Let me get you scheduled with one of our solution specialists who can give you the full demonstration. Thank you for your time today - I'm confident you'll find this valuable."

#### Objection Handling:
- **Price Concerns**: "I understand budget is important. That's exactly why I'd like to show you the ROI our clients typically see. Would a brief demo help you evaluate the value?"
- **No Time**: "I appreciate you're busy - that's actually why our solution is so valuable. Could we find just 15 minutes this week?"
- **Need to Think**: "Absolutely, this is an important decision. What specific information would help you think through this decision?"
- **Using Competitor**: "That's great that you have something in place. What would need to be different for you to consider a change?"

#### Company Information:
Elite Solutions Inc. specializes in business automation software that helps companies streamline operations, reduce manual processes, and increase productivity. We serve businesses from 10-500 employees across various industries with customized solutions and exceptional support.""",
            "welcome_message": "Hi! This is Sarah from Elite Solutions. I'm calling because you expressed interest in our business automation software. Do you have a few minutes to chat?",
            "stt_config_key": "DEEPGRAM_NOVA2_EN",
            "llm_config_key": "OPENAI_GPT4O_MINI",
            "tts_config_key": "CARTESIA_DEFAULT_EN",
            "initial_context": {
                "stage": "opening",
                "required_fields": [
                    "contact_name", "company_name", "industry", "company_size",
                    "current_system", "main_challenge", "impact_assessment",
                    "decision_authority", "timeline"
                ]
            },
            "business_config": {
                "business_type": "sales_consultation",
                "required_fields": [
                    "contact_name", "company_name", "industry", "company_size",
                    "current_system", "main_challenge", "impact_assessment",
                    "decision_authority", "timeline"
                ],
                "stage_map": {
                    "opening": 1,
                    "permission": 2,
                    "discovery": 3,
                    "pain_identification": 4,
                    "impact_assessment": 5,
                    "solution_bridge": 6,
                    "demo_proposal": 7,
                    "closing": 8
                },
                "question_map": {
                    "contact_name": "May I have your name please?",
                    "company_name": "What's the name of your company?",
                    "industry": "What industry are you in?",
                    "company_size": "How many employees do you currently have?",
                    "current_system": "What systems are you using now for your business operations?",
                    "main_challenge": "What's the biggest challenge you're facing with your current setup?",
                    "impact_assessment": "How much time per week does this issue cost you?",
                    "decision_authority": "Are you the person who would make the decision on a solution like this?",
                    "timeline": "When are you looking to have a solution in place?"
                }
            }
        },
        "outbound": {
            # Placeholder for outbound config, can be filled later
        }
    },
    "+15559876543": {
        "inbound": {
            "assistant_instructions": """You are a friendly restaurant reservation assistant for 'Chez Marie'.
Help customers make reservations and answer questions about the menu.
Be warm, welcoming, and efficient.
""",
            "welcome_message": "Bonjour! Welcome to Chez Marie. I'm here to help you with reservations. How can I assist you today?",
            "stt_config_key": "DEEPGRAM_NOVA2_EN",
            "llm_config_key": "OPENAI_GPT4O_MINI",
            "tts_config_key": "CARTESIA_DEFAULT_EN",
            "initial_context": {
                "stage": "greeting",
                "required_fields": ["customer_name", "party_size", "preferred_date", "preferred_time"]
            },
            "business_config": {
                "business_type": "restaurant",
                "required_fields": ["customer_name", "party_size", "preferred_date", "preferred_time"],
                "stage_map": {
                    "greeting": 1,
                    "reservation_details": 2,
                    "confirmation": 3,
                    "closing": 4
                },
                "question_map": {
                    "customer_name": "May I have your name for the reservation?",
                    "party_size": "How many people will be joining you?",
                    "preferred_date": "What date would you prefer?",
                    "preferred_time": "What time would work best for you?"
                }
            }
        },
        "outbound": {
            # Placeholder for outbound config, can be filled later
        }
    },
    "+15559999999": {
        "inbound": {
            "assistant_instructions": """#### Role:
You are Alex, an intelligent AI assistant for 'Smart Business Hub', equipped with advanced capabilities to help customers with information queries, appointment booking, and business tasks.

#### Personality:
- You are intelligent, efficient, and helpful
- You can access real-time information and perform actions
- You explain what you're doing when accessing external systems
- You're proactive in offering relevant services
- You maintain a professional yet friendly demeanor

#### API Capabilities:
You have access to several powerful capabilities:
1. **Knowledge Query**: You can search our vector database to answer specific questions about products, services, policies, and procedures
2. **Appointment Booking**: You can check availability and book appointments in real-time
3. **Information Retrieval**: You can fetch customer records and account information
4. **Task Execution**: You can perform various business tasks through API integrations

#### Instructions:
When customers ask questions:
1. If they ask for specific information (policies, procedures, product details), use your knowledge query capability
2. If they want to book appointments, check availability first, then book if desired
3. If they need account information, offer to look it up for them
4. Always explain what you're doing: "Let me check our database for that information" or "I'll look up available appointments for you"

#### Communication Style:
- Be conversational and natural
- Explain your actions: "I'm checking our appointment system now..."
- Provide specific, accurate information from your queries
- Offer follow-up actions: "Would you like me to book that appointment for you?"
- Handle errors gracefully: "I'm having trouble accessing that information right now, let me try another way"

#### Process Flow:
1. **Greeting**: Welcome the customer and ask how you can help
2. **Identify Need**: Determine if they need information, appointments, or other services
3. **Use Capabilities**: Query knowledge base, check availability, or perform actions as needed
4. **Provide Results**: Share findings and offer next steps
5. **Follow-up**: Ask if there's anything else you can help with

#### Examples of API Usage:
- Customer asks "What's your return policy?" → Query knowledge base
- Customer says "I need an appointment" → Check availability, then book
- Customer asks "What services do you offer?" → Query knowledge base for services
- Customer wants to reschedule → Look up existing appointment, check new availability""",
            "welcome_message": "Hi! I'm Alex from Smart Business Hub. I can help you with information, appointments, and various services. What can I assist you with today?",
            "stt_config_key": "DEEPGRAM_NOVA2_EN",
            "llm_config_key": "OPENAI_GPT4O_MINI",
            "tts_config_key": "CARTESIA_DEFAULT_EN",
            "initial_context": {
                "stage": "greeting",
                "required_fields": ["customer_name", "inquiry_type", "specific_request"]
            },
            "business_config": {
                "business_type": "ai_assistant",
                "required_fields": ["customer_name", "inquiry_type", "specific_request"],
                "stage_map": {
                    "greeting": 1,
                    "need_identification": 2,
                    "information_retrieval": 3,
                    "action_execution": 4,
                    "follow_up": 5
                },
                "question_map": {
                    "customer_name": "May I have your name please?",
                    "inquiry_type": "What type of assistance are you looking for today?",
                    "specific_request": "Can you tell me more specifically what you need help with?"
                }
            }
        },
        "outbound": {
            # Placeholder for outbound config, can be filled later
        }
    },
    "default": {
        "inbound": {
            "assistant_instructions": "You are a default assistant. Please state that this number is not configured and hang up politely.",
            "welcome_message": "Hello. This phone number has not been configured yet. Please contact support. Goodbye.",
            "stt_config_key": "DEEPGRAM_NOVA2_EN",
            "llm_config_key": "OPENAI_GPT4O_MINI",
            "tts_config_key": "CARTESIA_DEFAULT_EN",
            "initial_context": {
                "stage": "error",
                "required_fields": []
            },
            "business_config": {
                "business_type": "default",
                "required_fields": [],
                "stage_map": {"error": 1},
                "question_map": {}
            }
        },
        "outbound": {
            # Placeholder for outbound config, can be filled later
        }
    }
}


async def get_agent_config_from_db_by_phone(phone_number: str, call_type: str = "inbound") -> Optional[Dict[str, Any]]:
    """
    Simulates fetching an agent's configuration from a database using a phone number and call type.

    Args:
        phone_number: The phone number that received the call.
        call_type: "inbound" or "outbound" (default: "inbound")

    Returns:
        A dictionary with the agent's configuration if found, otherwise None.
    """
    print(
        f"DATABASE: Querying for agent config with phone_number: {phone_number}, call_type: {call_type}")

    # 1) Try Redis cache first
    try:
        redis_client = await get_redis_connection()
        cache_key = f"agent_config:{phone_number}:{call_type}"
        cached = await redis_client.get(cache_key)
        if cached:
            print(f"DATABASE: Cache hit for {cache_key}")
            return json.loads(cached)
        else:
            print(f"DATABASE: Cache miss for {cache_key}")
    except Exception as e:
        print(f"DATABASE: Redis not available, skipping cache. Error: {e}")

    # 2) Try external config service (token-based or legacy), then cache
    config_from_api = None
    token_url = (
        os.getenv("VOICE_CONFIG_TOKEN_URL")
        or (os.getenv("BACKEND_BASE_URL") + "/api/v1/voice-config/get-by-token/")
        if os.getenv("BACKEND_BASE_URL")
        else None
    )
    jwt_secret = os.getenv("JWT_SECRET")

    # Debug all environment variables related to configuration
    print(
        f"DATABASE DEBUG: VOICE_CONFIG_TOKEN_URL = '{os.getenv('VOICE_CONFIG_TOKEN_URL')}'")
    print(
        f"DATABASE DEBUG: BACKEND_BASE_URL = '{os.getenv('BACKEND_BASE_URL')}'")
    print(
        f"DATABASE DEBUG: JWT_SECRET exists = {bool(jwt_secret)}, length = {len(jwt_secret) if jwt_secret else 0}")
    print(f"DATABASE DEBUG: Resolved token_url = '{token_url}'")
    print(
        f"DATABASE DEBUG: Environment variables: {sorted([k for k in os.environ.keys()])[:10]}")

    if token_url and jwt_secret:
        print(
            f"DATABASE: Will attempt token-based config fetch from {token_url}")
    else:
        print("DATABASE: No token URL or JWT secret configured, will skip token-based config fetch")

    try:
        async with APIClient() as client:
            api_config = await client.fetch_agent_config(phone_number, call_type)
            if api_config and isinstance(api_config, dict):
                # If API returns multi-call-type dict, select the requested call_type
                if call_type in api_config and isinstance(api_config[call_type], dict):
                    config_from_api = api_config.get(call_type)
                else:
                    config_from_api = api_config
                print("DATABASE: Loaded configuration from external API")
                # Cache it for future if Redis is available
                try:
                    redis_client = await get_redis_connection()
                    cache_key = f"agent_config:{phone_number}:{call_type}"
                    await redis_client.set(cache_key, json.dumps(config_from_api), ex=300)
                    print(f"DATABASE: Cached config for {cache_key}")
                except Exception as e:
                    print(f"DATABASE: Could not cache config: {e}")
    except Exception as e:
        print(f"DATABASE: External API fetch failed: {e}")

    if config_from_api:
        return config_from_api

    # 3) Fallback to hardcoded configuration
    print("DATABASE: Falling back to hardcoded configuration")
    await asyncio.sleep(0.05)  # Simulate small latency
    phone_configs = AGENT_CONFIG_DB.get(phone_number)
    if phone_configs:
        config = phone_configs.get(call_type)
        if config:
            print(
                f"DATABASE: Found hardcoded configuration for phone number {phone_number} and call_type {call_type}")
            return config
        else:
            print(
                f"DATABASE: No hardcoded configuration found for phone number {phone_number} and call_type {call_type}")
            return None
    else:
        print(
            f"DATABASE: No hardcoded configuration found for phone number {phone_number}")
        return None


async def get_agent_config_from_db(user_id: str, call_type: str = "inbound") -> Optional[Dict[str, Any]]:
    """
    Simulates fetching an agent's configuration from a database.

    Args:
        user_id: The ID of the user or agent configuration to fetch.
        call_type: "inbound" or "outbound" (default: "inbound")

    Returns:
        A dictionary with the agent's configuration if found, otherwise None.
    """
    print(
        f"DATABASE: Querying for agent config with user_id: {user_id}, call_type: {call_type}")

    # Delegate to phone-based getter (user_id may be a phone number or "default")
    return await get_agent_config_from_db_by_phone(user_id, call_type)
