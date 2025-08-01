
from typing import List, Optional, Dict
from config import access_token, phone_number_id, whatsapp_api_version
import httpx
# Base URL for WhatsApp API
API_URL = f"https://graph.facebook.com/{whatsapp_api_version}/{phone_number_id}/messages"

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

async def send_text_message(to: str, message: str) -> Dict:
    """
    Send a text message via WhatsApp API.

    Args:
        to (str): Recipient phone number with country code (e.g., "+1234567890").
        message (str): The text message content.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, headers=HEADERS, json=payload)
        return response.json()

async def send_template_message_with_no_params(
    to: str,
    template_name: str,
    lang_code: str
) -> Dict:
    """
    Send a WhatsApp template message without parameters.

    Args:
        to (str): Recipient phone number with country code.
        template_name (str): Name of the approved WhatsApp template.
        lang_code (str): Language code for the template (e.g., "en_US").

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang_code}
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=30.0)
        return response.json()



# ============================ STARTING FROM HERE==============================

async def send_language_selection_prompt(to: str,text:str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "english_lang",
                            "title": "English"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "swahili_lang",
                            "title": "Swahili"
                        }
                    }
                ]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            API_URL,
            headers=HEADERS,
            json=payload,             
            timeout=30.0
        )
        # if not response:
        #     return random("swahili","english")
        # else:
        return response.json()

async def send_template_message(
    to: str,
    template_name: str,
    lang_code: str,
    parameters: Optional[List[str]] = None,
    expected_params: int = 0
) -> Dict:
    """
    Send a WhatsApp template message with optional parameters and validation.

    Args:
        to (str): Recipient phone number with country code.
        template_name (str): Name of the approved WhatsApp template.
        lang_code (str): Language code for the template (e.g., "en_US").
        parameters (Optional[List[str]]): List of parameter values for the template.
        expected_params (int): Number of parameters the template expects.

    Returns:
        Dict: JSON response from the WhatsApp API or error details.

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    parameters = parameters or []

    # Validate parameter count
    if len(parameters) != expected_params:
        return {
            "error": {
                "message": f"Template expects {expected_params} parameters, got {len(parameters)}",
                "code": "param_count_mismatch"
            }
        }

    # Format parameters for the API
    formatted_parameters = [
        {"type": "text", "text": str(param).strip()}
        for param in parameters
        if param and str(param).strip()
    ] if expected_params > 0 else []

    # Build the payload
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang_code}
        }
    }

    # Add components if parameters are expected
    if expected_params > 0:
        payload["template"]["components"] = [{
            "type": "body",
            "parameters": formatted_parameters
        }]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(API_URL, headers=HEADERS, json=payload, timeout=30.0)
            return response.json()
    except Exception as e:
        return {
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "code": "request_failed"
            }
        }

async def send_flow_message(
    to: str,
    flow_name: str = "jenga survey",
    flow_id: str = "",
    
) -> Dict:
    """
    Send an interactive WhatsApp flow message.

    Args:
        to (str): Recipient phone number with country code.
        flow_name (str): Name of the flow (default: "jenga survey").
        flow_id (str): ID of the WhatsApp flow.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        httpx.HTTPError: If the API request fails.
    """
    # This was testing if things are working if we could modify them from the backend
    if flow_name == "azam_v1": # this 
        flow_cta="Kata ticketi"
        text = "Tadhali jaza taarifa zifuatazo kwa uashihi kukata ticketi"
    else:
        flow_cta = "Book a Ticket"
        text = "Please fill the following information correctly"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": flow_name
            },
            "body": {
                "text": text
            },
            "footer": {
                "text": "Powered by Neurotech"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_id": flow_id,
                    "flow_cta": "Start Survey",
                    "flow_message_version": "3"
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code != 200:
            print("Failed response:", response.status_code, response.text)
            response.raise_for_status()  # This will show detailed error

        return response.json()

