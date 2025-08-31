"""
Business tools for dynamic agent configurations
Handles client context, information collection, business logic, and API integrations
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from .api_client import query_knowledge_base, execute_api_action


class DynamicBusinessAgent:
    """Business logic for dynamic agent configurations based on phone number settings"""

    def __init__(self, business_config: Dict[str, Any] = None):
        self.client_info = {}
        self.conversation_stage = "introduction"

        # Load configuration from business_config or use generic defaults
        if business_config:
            self.required_fields = business_config.get("required_fields", [])
            self.stage_map = business_config.get("stage_map", {
                "introduction": 1,
                "info_collection": 2,
                "validation": 3,
                "solution_presentation": 4,
                "transfer_proposal": 5,
                "closing": 6
            })
            self.question_map = business_config.get("question_map", {})
            self.business_type = business_config.get(
                "business_type", "default")
            self.language = business_config.get("language", "en")
        else:
            # Generic defaults - no business-specific assumptions
            self.required_fields = ["customer_name", "inquiry_type"]
            self.stage_map = {
                "introduction": 1,
                "info_collection": 2,
                "validation": 3,
                "closing": 4
            }
            self.question_map = {
                "customer_name": "May I have your name please?",
                "inquiry_type": "How can I help you today?"
            }
            self.business_type = "generic"
            self.language = "en"

    async def update_conversation_stage(self, stage: str):
        """Update the current conversation stage"""
        if stage in self.stage_map:
            self.conversation_stage = stage
            print(f"Conversation stage updated to: {stage}")
        return self.conversation_stage

    async def collect_client_info(self, field: str, value: str) -> bool:
        """Collect and validate client information"""
        if field in self.required_fields:
            self.client_info[field] = value
            self.client_info[f"{field}_collected_at"] = datetime.now(
            ).isoformat()
            print(f"Collected {field}: {value}")
            return True
        return False

    async def get_missing_fields(self) -> list:
        """Get list of required fields that haven't been collected"""
        return [field for field in self.required_fields if field not in self.client_info]

    async def is_collection_complete(self) -> bool:
        """Check if all required information has been collected"""
        return len(await self.get_missing_fields()) == 0

    async def get_client_summary(self) -> str:
        """Generate a summary of collected client information"""
        if not self.client_info:
            return "No information collected" if self.language == "en" else "Aucune information collectée"

        summary_parts = []

        # Generic fields that work across business types
        name_fields = []
        if "first_name" in self.client_info:
            name_fields.append(self.client_info["first_name"])
        if "last_name" in self.client_info:
            name_fields.append(self.client_info["last_name"])
        if "customer_name" in self.client_info:
            name_fields.append(self.client_info["customer_name"])
        if "contact_name" in self.client_info:
            name_fields.append(self.client_info["contact_name"])

        if name_fields:
            name_label = "Name" if self.language == "en" else "Nom"
            summary_parts.append(f"{name_label}: {' '.join(name_fields)}")

        # Business-specific summaries
        if self.business_type == "social_housing":
            summary_parts.extend(self._get_social_housing_summary())
        elif self.business_type == "sales_consultation":
            summary_parts.extend(self._get_sales_summary())
        elif self.business_type == "restaurant":
            summary_parts.extend(self._get_restaurant_summary())
        elif self.business_type == "tech_support":
            summary_parts.extend(self._get_tech_support_summary())
        else:
            # Generic summary for unknown business types
            for field, value in self.client_info.items():
                if field not in ["first_name", "last_name", "customer_name", "contact_name"] and not field.endswith("_collected_at"):
                    summary_parts.append(
                        f"{field.replace('_', ' ').title()}: {value}")

        return "; ".join(summary_parts) if summary_parts else ("Basic information collected" if self.language == "en" else "Informations de base collectées")

    def _get_social_housing_summary(self) -> List[str]:
        """Generate summary for social housing business type"""
        parts = []

        if "department" in self.client_info:
            parts.append(f"Département: {self.client_info['department']}")
        if "housing_status" in self.client_info:
            parts.append(
                f"Statut logement: {self.client_info['housing_status']}")
        if "household_size" in self.client_info:
            parts.append(
                f"Taille du foyer: {self.client_info['household_size']} personnes")
        if "monthly_income" in self.client_info:
            parts.append(
                f"Revenus mensuels: {self.client_info['monthly_income']} euros")

        # Special situations
        special_situations = []
        if self.client_info.get("is_insalubrious") == "oui":
            special_situations.append("logement insalubre")
        if self.client_info.get("has_disability") == "oui":
            special_situations.append("situation de handicap")
        if self.client_info.get("expulsion_threat") == "oui":
            special_situations.append("menace d'expulsion")

        if special_situations:
            parts.append(
                f"Situations particulières: {', '.join(special_situations)}")

        return parts

    def _get_sales_summary(self) -> List[str]:
        """Generate summary for sales consultation business type"""
        parts = []

        if "company_name" in self.client_info:
            parts.append(f"Company: {self.client_info['company_name']}")
        if "industry" in self.client_info:
            parts.append(f"Industry: {self.client_info['industry']}")
        if "company_size" in self.client_info:
            parts.append(
                f"Company Size: {self.client_info['company_size']} employees")
        if "main_challenge" in self.client_info:
            parts.append(
                f"Main Challenge: {self.client_info['main_challenge']}")
        if "decision_authority" in self.client_info:
            parts.append(
                f"Decision Maker: {self.client_info['decision_authority']}")

        return parts

    def _get_restaurant_summary(self) -> List[str]:
        """Generate summary for restaurant business type"""
        parts = []

        if "party_size" in self.client_info:
            parts.append(
                f"Party Size: {self.client_info['party_size']} people")
        if "preferred_date" in self.client_info:
            parts.append(
                f"Preferred Date: {self.client_info['preferred_date']}")
        if "preferred_time" in self.client_info:
            parts.append(
                f"Preferred Time: {self.client_info['preferred_time']}")

        return parts

    def _get_tech_support_summary(self) -> List[str]:
        """Generate summary for tech support business type"""
        parts = []

        if "product_id" in self.client_info:
            parts.append(f"Product: {self.client_info['product_id']}")
        if "issue_description" in self.client_info:
            parts.append(f"Issue: {self.client_info['issue_description']}")
        if "issue_severity" in self.client_info:
            parts.append(f"Severity: {self.client_info['issue_severity']}")

        return parts

    async def determine_next_question(self) -> Optional[str]:
        """Determine the next question to ask based on current state"""
        missing_fields = await self.get_missing_fields()

        if not missing_fields:
            return None

        # Use configured question mapping
        return self.question_map.get(missing_fields[0], f"Can you provide information about {missing_fields[0]}?")

    async def assess_eligibility(self) -> Dict[str, Any]:
        """Assess client eligibility based on business type"""
        assessment = {
            "eligible": True,
            "priority_factors": [],
            "recommended_action": "standard_application",
            "notes": [],
            "business_type": self.business_type
        }

        # Business-specific eligibility logic
        if self.business_type == "social_housing":
            return await self._assess_social_housing_eligibility(assessment)
        elif self.business_type == "tech_support":
            return await self._assess_tech_support_eligibility(assessment)
        elif self.business_type == "restaurant":
            return await self._assess_restaurant_eligibility(assessment)
        else:
            # Generic assessment
            assessment["notes"].append("generic_assessment")
            return assessment

    async def _assess_social_housing_eligibility(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Social housing specific eligibility assessment"""
        # Check priority factors
        if self.client_info.get("is_insalubrious") == "oui":
            assessment["priority_factors"].append("logement_insalubre")

        if self.client_info.get("has_disability") == "oui":
            assessment["priority_factors"].append("handicap")

        if self.client_info.get("expulsion_threat") == "oui":
            assessment["priority_factors"].append("expulsion")
            assessment["recommended_action"] = "urgent_dalo"

        # Income assessment (simplified)
        if "monthly_income" in self.client_info:
            try:
                income = float(self.client_info["monthly_income"].replace(
                    "€", "").replace(",", "."))
                household_size = int(self.client_info.get("household_size", 1))

                # Simplified income thresholds (actual thresholds vary by region)
                income_threshold = 1500 * household_size  # Basic threshold

                if income > income_threshold * 1.5:
                    assessment["eligible"] = False
                    assessment["notes"].append("revenus_trop_eleves")
                elif income < income_threshold * 0.3:
                    assessment["priority_factors"].append(
                        "revenus_tres_faibles")
            except (ValueError, TypeError):
                assessment["notes"].append("revenus_a_verifier")

        return assessment

    async def _assess_tech_support_eligibility(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Tech support specific assessment"""
        if "product_id" in self.client_info:
            assessment["priority_factors"].append("product_identified")
        if "issue_severity" in self.client_info and self.client_info["issue_severity"] == "critical":
            assessment["recommended_action"] = "urgent_escalation"
        return assessment

    async def _assess_restaurant_eligibility(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Restaurant specific assessment"""
        if "party_size" in self.client_info:
            party_size = int(self.client_info.get("party_size", 1))
            if party_size > 8:
                assessment["recommended_action"] = "large_party_reservation"
        return assessment

    async def query_information(self, query: str) -> str:
        """Query vector database for information relevant to the business type"""
        context = {
            "business_type": self.business_type,
            "conversation_stage": self.conversation_stage,
            "client_info": self.client_info,
            "required_fields": self.required_fields
        }

        try:
            response = await query_knowledge_base(query, context)
            print(f"Knowledge base query: {query} -> {response[:100]}...")
            return response
        except Exception as e:
            print(f"Error querying knowledge base: {e}")
            return "I'm sorry, I couldn't retrieve that information right now. Let me help you in another way."

    async def execute_action(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute external API actions based on business needs"""
        try:
            # Add business context to parameters
            enhanced_parameters = {
                **parameters,
                "business_type": self.business_type,
                "conversation_stage": self.conversation_stage,
                "client_info": self.client_info
            }

            result = await execute_api_action(action, enhanced_parameters)
            print(f"Executed action {action}: {result.get('success', False)}")
            return result
        except Exception as e:
            print(f"Error executing action {action}: {e}")
            return {
                "success": False,
                "message": f"Unable to complete {action} at this time",
                "error": str(e)
            }

    async def handle_appointment_booking(self, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment booking for various business types"""
        # Validate required fields based on business type
        required_fields = ["customer_name", "preferred_date", "preferred_time"]

        if self.business_type == "restaurant":
            required_fields.extend(["party_size"])
        elif self.business_type == "tech_support":
            required_fields.extend(["service_type", "issue_description"])
        elif self.business_type == "social_housing":
            required_fields.extend(["department", "housing_status"])

        missing_fields = [
            field for field in required_fields if not appointment_details.get(field)]

        if missing_fields:
            return {
                "success": False,
                "message": f"Missing required information: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }

        # Book the appointment
        return await self.execute_action("book_appointment", appointment_details)

    async def check_availability(self, date: str, service_type: str = None) -> Dict[str, Any]:
        """Check availability for appointments"""
        return await self.execute_action("check_availability", {
            "date": date,
            "service_type": service_type or self.business_type
        })

    async def update_customer_record(self, additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Update customer record in CRM"""
        crm_data = {
            "phone_number": additional_info.get("phone_number") if additional_info else None,
            "name": f"{self.client_info.get('first_name', '')} {self.client_info.get('last_name', '')}".strip(),
            "email": self.client_info.get("email"),
            "company": self.client_info.get("company_name"),
            "interaction_type": "phone_call",
            "stage": self.conversation_stage,
            "notes": f"Business type: {self.business_type}, Stage: {self.conversation_stage}",
            "lead_score": self._calculate_lead_score()
        }

        if additional_info:
            crm_data.update(additional_info)

        return await self.execute_action("update_crm", crm_data)

    def _calculate_lead_score(self) -> int:
        """Calculate basic lead score based on collected information"""
        score = 0

        # Base score for engagement
        score += len(self.client_info) * 10

        # Business-specific scoring
        if self.business_type == "sales_consultation":
            if self.client_info.get("decision_authority") == "yes":
                score += 30
            if self.client_info.get("timeline") in ["immediate", "this_month"]:
                score += 20
        elif self.business_type == "restaurant":
            if self.client_info.get("party_size"):
                try:
                    party_size = int(self.client_info["party_size"])
                    # Larger parties are more valuable
                    score += min(party_size * 5, 25)
                except (ValueError, TypeError):
                    pass

        return min(score, 100)  # Cap at 100

    async def get_conversation_context(self) -> Dict[str, Any]:
        """Get complete conversation context for agent"""
        return {
            "stage": self.conversation_stage,
            "stage_number": self.stage_map.get(self.conversation_stage, 0),
            "client_info": self.client_info,
            "missing_fields": await self.get_missing_fields(),
            "completion_rate": (len(self.required_fields) - len(await self.get_missing_fields())) / len(self.required_fields) if self.required_fields else 1.0,
            "next_question": await self.determine_next_question(),
            "eligibility": await self.assess_eligibility() if await self.is_collection_complete() else None,
            "business_type": self.business_type,
            "api_capabilities": {
                "can_query_knowledge": True,
                "can_book_appointments": True,
                "can_check_availability": True,
                "can_update_crm": True
            }
        }


class ContextManager:
    """Manages conversation context and state for multiple business types"""

    def __init__(self):
        self.sessions = {}
        self.business_configs = {}

    async def get_session(self, user_id: str, business_config: Dict[str, Any] = None) -> DynamicBusinessAgent:
        """Get or create a session for a user with specific business configuration"""
        if user_id not in self.sessions:
            self.sessions[user_id] = DynamicBusinessAgent(business_config)
            if business_config:
                self.business_configs[user_id] = business_config
        return self.sessions[user_id]

    async def clear_session(self, user_id: str):
        """Clear a user's session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
        if user_id in self.business_configs:
            del self.business_configs[user_id]

    async def get_all_sessions(self) -> Dict[str, DynamicBusinessAgent]:
        """Get all active sessions (for debugging)"""
        return self.sessions

    async def update_business_config(self, user_id: str, business_config: Dict[str, Any]):
        """Update business configuration for an existing session"""
        if user_id in self.sessions:
            # Update existing session with new config
            self.sessions[user_id] = DynamicBusinessAgent(business_config)
            self.business_configs[user_id] = business_config


# Global context manager instance
context_manager = ContextManager()


async def get_business_context(user_id: str, business_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get business context for a user with optional business configuration"""
    session = await context_manager.get_session(user_id, business_config)
    return await session.get_conversation_context()


async def update_client_info(user_id: str, field: str, value: str) -> bool:
    """Update client information for a user"""
    session = await context_manager.get_session(user_id)
    return await session.collect_client_info(field, value)


async def advance_conversation_stage(user_id: str, stage: str) -> str:
    """Advance conversation to next stage"""
    session = await context_manager.get_session(user_id)
    return await session.update_conversation_stage(stage)


async def query_user_information(user_id: str, query: str) -> str:
    """Query knowledge base for user-specific information"""
    session = await context_manager.get_session(user_id)
    return await session.query_information(query)


async def book_user_appointment(user_id: str, appointment_details: Dict[str, Any]) -> Dict[str, Any]:
    """Book appointment for user"""
    session = await context_manager.get_session(user_id)
    return await session.handle_appointment_booking(appointment_details)


async def check_user_availability(user_id: str, date: str, service_type: str = None) -> Dict[str, Any]:
    """Check availability for user"""
    session = await context_manager.get_session(user_id)
    return await session.check_availability(date, service_type)


async def update_user_crm(user_id: str, additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Update user CRM record"""
    session = await context_manager.get_session(user_id)
    return await session.update_customer_record(additional_info)
