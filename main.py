from fastapi import FastAPI, Query, HTTPException, Request
from typing import Optional
import logging
from whatsapp import (
    send_text_message,
    send_template_message,
    send_template_message_with_no_params,   
    send_flow_message
)

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
def root():
    return {"message": "WhatsApp Flow Testing Backend (No Webhook)"}

@app.post("/send-text")
async def send_text(
    to: str = Query(..., description="WhatsApp number with country code"),
    message: str = Query(..., description="Message body")
):
    try:
        return await send_text_message(to, message)
    except Exception as e:
        logger.error(f"Error sending text message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send text message")

@app.post("/send-template-no-params")
async def send_template_(
    to: str = Query(..., description="WhatsApp number with country code"),
    template_name: str = Query(..., description="Template name"),
    lang_code: str = Query(..., description="Language code registered at Meta")):
    
    result = await send_template_message_with_no_params(to=to,template_name=template_name,lang_code=lang_code)
    return result

@app.post("/send-template")
async def send_template(
    to: str = Query(..., description="WhatsApp number with country code"),
    template_name: str = Query(..., description="Template name"),
    lang_code: str = Query(..., description="Language code registered at Meta"),
    expected_params: int = Query(0, description="Number of parameters the template expects"),
    param1: Optional[str] = Query(None, description="First template parameter"),
    param2: Optional[str] = Query(None, description="Second template parameter")
):
    # Prepare parameters based on expected count
    parameters = []
    if expected_params > 0:
        parameters = [p for p in [param1, param2][:expected_params] if p is not None]
    
    try:
        result = await send_template_message(
            to=to,
            template_name=template_name,
            lang_code=lang_code,
            parameters=parameters,
            expected_params=expected_params
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
        
    except Exception as e:
        logger.error(f"Error sending template: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send template")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received webhook data: {data}")

        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        button_reply = message.get("button", {}).get("text")

        if button_reply:
            if "English" in button_reply:
                return await send_flow_message(
                    to=sender,
                    flow_name="azam_v1_english",
                    flow_id="english_flow_id"
                )
            elif "Swahili" in button_reply:
                return await send_flow_message(
                    to=sender,
                    flow_name="azam_v1_swahili",
                    flow_id="swahili_flow_id"
                )
        return {"status": "no action taken"}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/send-language-choice")
async def trigger_language_flow(
    language: str = Query(..., description="Language choice (english/swahili)"),
    recipient: str = Query(..., description="Recipient's WhatsApp number")
):
    language = language.lower()
    
    if language == "english":
        flow_id = "713784581492733"
        flow_name = "azam_v2"
    elif language == "swahili":
        flow_id = "552112574623758"
        flow_name = "azam_v1"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid language parameter. Choose 'english' or 'swahili'"
        )

    try:
        return await send_flow_message(
            to=recipient,
            flow_name=flow_name,
            flow_id=flow_id
        )
    except Exception as e:
        logger.error(f"Error sending flow message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send {language} flow message"
        )
