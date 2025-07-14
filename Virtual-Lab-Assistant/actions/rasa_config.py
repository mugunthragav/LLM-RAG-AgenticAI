from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import logging

# Logger Configuration
rasa_logger = logging.getLogger("rasa_config")
rasa_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/rasa_config_logs.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
rasa_logger.addHandler(file_handler)

# Constants
STATIC_INTENTS = [
    "greet",
    "goodbye",
    "fuel_cell_types",
    "hydrogen_fuel_cell_basics",
    "fuel_cell_components",
    "fuel_cell_efficiency",
    "fuel_cell_troubleshooting",
    "list_of_labs",
    "voltage_issues",
    "membrane_issues",
    "gas_flow_issues",
    "performance_measurement",
    "data_analysis",
    "maintenance_procedures",
    "parameter_optimization",
    "experiment_help",
    "results_interpretation",
    "component_info",
    "equipment_setup"

]

DYNAMIC_INTENTS = [
    "check_parameter_limits",
    "get_safety_guidelines",
    "get_emergency_procedure",
    "check_performance_metrics",
    "available_labs",
    "lab_equipment",
    "experiment_help"
]

RAG_INTENTS = ["query_rag"]
FASTAPI_LLM_URL = "http://llm:8001/"
FASTAPI_RAG_URL = "http://rag:8002/"

# Thresholds
STATIC_THRESHOLD = 0.90
DYNAMIC_THRESHOLD = 0.80
RAG_THRESHOLD = 0.75

class ActionFetchResponse(Action):
    def name(self) -> Text:
        return "action_fetch_response"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent_info = tracker.latest_message["intent"]
        intent = intent_info.get("name")
        confidence = intent_info.get("confidence", 0)
        user_message = tracker.latest_message.get("text", "")

        rasa_logger.info(f"User Query: {user_message}")
        rasa_logger.info(f"Detected Intent: {intent} with Confidence: {confidence:.2f}")

        # STATIC
        if intent in STATIC_INTENTS:
            if confidence >= STATIC_THRESHOLD:
                rasa_logger.info(f"Static intent '{intent}' passed threshold.")
                return []
            else:
                rasa_logger.warning(f"Static intent '{intent}' below threshold. Falling back to LLM.")

        # DYNAMIC
        elif intent in DYNAMIC_INTENTS:
            if confidence >= DYNAMIC_THRESHOLD:
                try:
                    response = requests.post(
                        f"{FASTAPI_LLM_URL}/fetch_dynamic_response/",
                        json={"intent": intent, "query": user_message},
                        timeout=60
                    )
                    response.raise_for_status()
                    data = response.json()
                    reply = data.get("response")
                    if reply and reply != "I couldn't find a matching entry in the database.":
                        dispatcher.utter_message(text=reply)
                        return []
                    rasa_logger.warning("No DB match. Falling back to LLM.")
                except requests.RequestException as e:
                    rasa_logger.error(f"Dynamic API error: {e}")
            else:
                rasa_logger.warning(f"Dynamic intent below threshold. Falling back to LLM.")

        # RAG
        elif intent in RAG_INTENTS:
            if confidence >= RAG_THRESHOLD:
                try:
                    response = requests.get(
                        f"{FASTAPI_RAG_URL}/rag_query/",
                        params={"query": user_message},
                        timeout=60
                    )
                    response.raise_for_status()
                    data = response.json()
                    reply = data.get("response")
                    if reply and reply != "No relevant document found.":
                        dispatcher.utter_message(text=reply)
                        return []
                    rasa_logger.warning("RAG returned no doc. Falling back to LLM.")
                except requests.RequestException as e:
                    rasa_logger.error(f"RAG API error: {e}")
            else:
                rasa_logger.warning(f"RAG intent below threshold. Falling back to LLM.")

        # LLM Fallback
        try:
            response = requests.post(
                f"{FASTAPI_LLM_URL}/fetch_gpt_response/",
                json={"query": user_message},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            reply = data.get("response")
            if reply:
                dispatcher.utter_message(text=reply)
                return []
            dispatcher.utter_message(text="Sorry, I couldn't get a proper response.")
        except requests.RequestException as e:
            rasa_logger.error(f"LLM API Fallback Error: {e}")
            dispatcher.utter_message(text="LLM API error occurred. Please try again later.")

        return []

class ActionQueryRag(Action):
    def name(self) -> Text:
        return "action_query_rag"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        user_message = tracker.latest_message.get("text", "")
        confidence = tracker.latest_message["intent"].get("confidence", 0)

        rasa_logger.info(f"RAG Query: {user_message} with confidence {confidence:.2f}")

        try:
            response = requests.get(
                f"{FASTAPI_RAG_URL}/rag_query/",
                params={"query": user_message},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            reply = data.get("response")
            if reply and reply != "No relevant document found.":
                dispatcher.utter_message(text=reply)
                rasa_logger.info(f"RAG Response: {reply[:100]}...")
                return []
            rasa_logger.warning("RAG fallback: no relevant document.")
        except requests.RequestException as e:
            rasa_logger.error(f"RAG API Error: {e}")

        try:
            response = requests.post(
                f"{FASTAPI_LLM_URL}/fetch_gpt_response/",
                json={"query": user_message},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            reply = data.get("response")
            if reply:
                dispatcher.utter_message(text=reply)
                return []
            dispatcher.utter_message(text="Sorry, I couldn't get a proper response.")
        except requests.RequestException as e:
            rasa_logger.error(f"LLM fallback error from RAG: {e}")
            dispatcher.utter_message(text="LLM API error occurred. Please try again later.")

        return []
