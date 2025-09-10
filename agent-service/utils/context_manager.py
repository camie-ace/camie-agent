"""
Context manager for agent conversations
Handles user context, session state, and business logic integration
"""

import asyncio
from typing import Dict, Any, Optional
from utils.business_tools import get_business_context, update_client_info, advance_conversation_stage


class ConversationContext:
    """Manages conversation context for an agent session"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_data = {}
        self.conversation_history = []
        self.business_context = {}

    async def initialize(self, initial_context: dict = None):
        """Initialize the conversation context"""
        # Extract business config from initial context if provided
        business_config = initial_context.get(
            "business_config") if initial_context else None

        self.business_context = await get_business_context(self.user_id, business_config)

        # Apply initial context from database if provided
        if initial_context:
            print(f"Applying initial context from database: {initial_context}")
            # Set initial stage if provided
            if "stage" in initial_context:
                self.business_context["stage"] = initial_context["stage"]
            # Set required fields if provided
            if "required_fields" in initial_context:
                self.business_context["required_fields"] = initial_context["required_fields"]
            # Apply any other initial context data (excluding business_config to avoid recursion)
            context_data = {
                k: v for k, v in initial_context.items() if k != "business_config"}
            self.business_context.update(context_data)

        print(f"Initialized context for user: {self.user_id}")

    async def update_business_info(self, field: str, value: str) -> bool:
        """Update business information"""
        success = await update_client_info(self.user_id, field, value)
        if success:
            # Refresh business context (no business_config needed for updates)
            self.business_context = await get_business_context(self.user_id)
        return success

    async def advance_stage(self, stage: str) -> str:
        """Advance conversation stage"""
        new_stage = await advance_conversation_stage(self.user_id, stage)
        # Refresh business context (no business_config needed for updates)
        self.business_context = await get_business_context(self.user_id)
        return new_stage

    async def get_current_context(self) -> Dict[str, Any]:
        """Get current conversation context"""
        # Refresh business context before returning (no business_config needed for refresh)
        self.business_context = await get_business_context(self.user_id)

        return {
            "user_id": self.user_id,
            "session_data": self.session_data,
            "business_context": self.business_context,
            "conversation_history_length": len(self.conversation_history)
        }

    async def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def get_next_action_suggestion(self) -> Optional[str]:
        """Get suggestion for next action based on current context"""
        if not self.business_context:
            return "Commencer par se présenter et expliquer la raison de l'appel"

        stage = self.business_context.get("stage", "introduction")
        missing_fields = self.business_context.get("missing_fields", [])
        next_question = self.business_context.get("next_question")

        if stage == "introduction":
            return "Se présenter et expliquer le but de l'appel"
        elif stage == "info_collection" and missing_fields:
            return f"Poser la prochaine question: {next_question}"
        elif stage == "info_collection" and not missing_fields:
            return "Valider les informations collectées"
        elif stage == "validation":
            return "Présenter la solution Pôle Démarches"
        elif stage == "solution_presentation":
            return "Proposer le transfert vers le département logement"
        else:
            return "Continuer selon le script établi"

    async def should_collect_info(self) -> bool:
        """Check if we should be collecting client information"""
        stage = self.business_context.get("stage", "introduction")
        return stage in ["info_collection", "validation"]

    async def get_completion_status(self) -> Dict[str, Any]:
        """Get conversation completion status"""
        completion_rate = self.business_context.get("completion_rate", 0)
        missing_fields = self.business_context.get("missing_fields", [])

        return {
            "completion_rate": completion_rate,
            "missing_field_count": len(missing_fields),
            "missing_fields": missing_fields,
            "is_complete": completion_rate >= 1.0
        }


# Global context store
active_contexts: Dict[str, ConversationContext] = {}


async def get_context_for_user(user_id: str, initial_context: dict = None) -> ConversationContext:
    """Get or create conversation context for a user"""
    # Handle session-based identification (not persistent user accounts)
    if user_id not in active_contexts:
        context = ConversationContext(user_id)
        await context.initialize(initial_context)
        active_contexts[user_id] = context
        print(f"Created new session context for: {user_id}")
    else:
        print(f"Reusing existing session context for: {user_id}")

    return active_contexts[user_id]


async def cleanup_context(user_id: str):
    """Clean up context for a user"""
    if user_id in active_contexts:
        del active_contexts[user_id]
        print(f"Cleaned up context for user: {user_id}")


async def get_context_summary(user_id: str) -> Dict[str, Any]:
    """Get a summary of the current context"""
    if user_id in active_contexts:
        context = active_contexts[user_id]
        return await context.get_current_context()
    return {"error": "No active context found"}
