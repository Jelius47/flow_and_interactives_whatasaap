import httpx
from config import access_token, phone_number_id,whatsapp_api_version

api_url = f"https://graph.facebook.com/{whatsapp_api_version}/{phone_number_id}/messages"
headers = {
    "authorization": f"bearer {access_token}",
    "content-type": "application/json"
}

async def send_text_message(to: str, message: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    async with httpx.asyncclient() as client:
        response = await client.post(api_url, headers=headers, json=payload)
        return response.json()
from typing import List, Optional

async def send_template_message(
    to: str,
    template_name: str,
    lang_code: str,
    parameters: Optional[List[str]] = None,
    expected_params: int = 0  # default to 0 if not specified
) -> dict:
    """
    send whatsapp template message with parameter validation
    
    args: 
        to: recipient phone number with country code
        template_name: approved template name
        lang_code: language code (e.g. en_us)
        parameters: list of parameter values (empty if no variables)
        expected_params: number of parameters the template expects
        
    returns:
        api response or error dictionary
    """
    # initialize parameters if none
    parameters = parameters or []
    
    # validate parameter count
    if len(parameters) != expected_params:
        return {
            "error": {
                "message": f"template expects {expected_params} parameters, got {len(parameters)}",
                "code": "param_count_mismatch"
            }
        }

    # format parameters (only if they exist)
    formatted_parameters = [
        {"type": "text", "text": str(param).strip()}
        for param in parameters
        if param and str(param).strip()
    ] if expected_params > 0 else []

    # build payload
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang_code}
        }
    }

    # add components only if template expects parameters
    if expected_params > 0:
        payload["template"]["components"] = [{
            "type": "body",
            "parameters": formatted_parameters
        }]

    try:
        async with httpx.asyncclient() as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            return response.json()
            
    except exception as e:
        return {
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "code": "request_failed"
            }
        }





async def send_flow_message(to: str, flow_name: str = "jenga survey",flow_id: str= "" ):
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
                "text": "please tap below to begin the survey."
            },
            "footer": {
                "text": "powered by whatsapp flows"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_id": flow_id,
                    "flow_cta": "start survey",
                    "flow_message_version": "3"
                    # optional: "flow_token": "{\"key\": \"value\"}" if using variables
                }
            }
        }
    }

    async with httpx.asyncclient() as client:
        response = await client.post(api_url, headers=headers, json=payload)
        return response.json()

    
