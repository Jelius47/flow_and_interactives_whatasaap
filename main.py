from fastapi import FastAPI, Query, HTTPException, Request ,Response,status
from typing import Optional, Dict

import json

from config import flow_config
from fastapi.responses import JSONResponse
from utils.security import Security

from models import BookingData
from datetime import datetime, timedelta
import traceback

import logging
from whatsapp import (
    send_text_message,
    send_template_message,
    send_template_message_with_no_params,
    send_flow_message,
    send_language_selection_prompt,
    register_business_encryption
)

# Initialize FastAPI app
app = FastAPI(title="WhatsApp Flow Testing API", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root() -> Dict:
    """
    Root endpoint for the WhatsApp Flow Testing Backend.

    Returns:
        Dict: Welcome message.
    """
    return {"message": "WhatsApp Flow Testing Backend (No Webhook)"}

@app.post("/send-text")
async def send_text(
    to: str = Query(..., description="WhatsApp number with country code (e.g., +1234567890)"),
    message: str = Query(..., description="Text message content")
) -> Dict:
    """
    Send a text message via WhatsApp.

    Args:
        to (str): Recipient phone number with country code.
        message (str): The text message content.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        HTTPException: If the message sending fails.
    """
    try:
        return await send_text_message(to, message)
    except Exception as e:
        logger.error(f"Error sending text message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send text message")

@app.post("/send-template-no-params")
async def send_template_no_params(
    to: str = Query(..., description="WhatsApp number with country code"),
    template_name: str = Query(..., description="Approved WhatsApp template name"),
    lang_code: str = Query(..., description="Language code registered at Meta (e.g., en_US)")
) -> Dict:
    """
    Send a WhatsApp template message without parameters.

    Args:
        to (str): Recipient phone number with country code.
        template_name (str): Name of the approved WhatsApp template.
        lang_code (str): Language code for the template.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        HTTPException: If the template sending fails.
    """
    try:
        return await send_template_message_with_no_params(to, template_name, lang_code)
    except Exception as e:
        logger.error(f"Error sending template without parameters: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send template")

@app.post("/send-template")
async def send_template(
    to: str = Query(..., description="WhatsApp number with country code"),
    template_name: str = Query(..., description="Approved WhatsApp template name"),
    lang_code: str = Query(..., description="Language code registered at Meta (e.g., en_US)"),
    expected_params: int = Query(0, description="Number of parameters the template expects"),
    param1: Optional[str] = Query(None, description="First template parameter"),
    param2: Optional[str] = Query(None, description="Second template parameter")
) -> Dict:
    """
    Send a WhatsApp template message with optional parameters.

    Args:
        to (str): Recipient phone number with country code.
        template_name (str): Name of the approved WhatsApp template.
        lang_code (str): Language code for the template.
        expected_params (int): Number of parameters the template expects.
        param1 (Optional[str]): First template parameter.
        param2 (Optional[str]): Second template parameter.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        HTTPException: If parameter validation fails or the template sending fails.
    """
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



# =============================================================================LETS START FROM HERE===================================================


@app.post("/register-encryption")
async def register():
    return await register_business_encryption()


from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
import json

@app.post("/flow-data")
async def flow_data(request: Request):
    """Flow data exchange endpoint with complete implementation."""
    try:
        data = await request.json()
        encrypted_flow_data = data.get("encrypted_flow_data")
        encrypted_aes_key = data.get("encrypted_aes_key")
        initial_vector = data.get("initial_vector")

        # Decrypt the incoming data
        decrypted_data, aes_key, iv = Security.decrypt_request(
            encrypted_flow_data_b64=encrypted_flow_data,
            encrypted_aes_key_b64=encrypted_aes_key,
            initial_vector_b64=initial_vector,
        )
        
        print(f"\nDecrypted data: {decrypted_data}")
        
        # Handle health check (ping)
        if decrypted_data.get("action") == "ping":
            print("Ping received - Flow is active")
            response = {
                "data": {
                    "status": "active",
                },
            }
            encrypted_response = Security.encrypt_response(
                response=response, aes_key=aes_key, iv=iv
            )
            return Response(
                content=encrypted_response,
                media_type="text/plain",
                status_code=status.HTTP_200_OK,
            )

        # Handle INIT action - Flow initialization
               
        if decrypted_data.get("action") == "INIT":
            flow_token = decrypted_data.get("flow_token")
            print(f"Flow initialization - Token: {flow_token}")
            
            # Initialize any session data you need
            initialize_flow_session(flow_token)
            
            # Return initial data with the screen property
            response = {
                "screen": "PERSONAL_INFO",  # Specify the first screen
                "data": {
                    "initialized": True,
                    "welcome_message": "Welcome to our booking system!"
                }
            }
            
            encrypted_response = Security.encrypt_response(
                response=response, aes_key=aes_key, iv=iv
            )
            return Response(
                content=encrypted_response,
                media_type="text/plain",
                status_code=status.HTTP_200_OK,
            )

        # Handle screen navigation and data requests
        current_screen = decrypted_data.get("screen")
        action = decrypted_data.get("action")
        flow_token = decrypted_data.get("flow_token")
        
        print(f"Current screen: {current_screen}, Action: {action}")

        # AVAILABILITY Screen - Send dynamic data to frontend
        if current_screen == "PERSONAL_INFO":
            # Your backend logic to fetch available time slots
            available_slots = get_available_time_slots(
                route=decrypted_data.get("going_route"),
                date=decrypted_data.get("going_date"),
                passengers=decrypted_data.get("going_no_passengers")
            )
            
            response = {
                "screen": "AVAILABILITY",
                "data": {
                    "going_availability_slots": [
            {
              "id": "04_08_2025$14_00",
              "title": "04-08-2025 at 14:00"
            },
            {
              "id": "04_08_2025$16_00",
              "title": "04-08-2025 at 16:00"
            }
          ]
                }
            }
            
        # SEATS Screen - Send seat categories and pricing
        elif current_screen == "SEATS":
            seat_categories = get_seat_categories()
            response = {
                "data": {
                    "seat_categories": seat_categories
                }
            }
            
        # Handle data_exchange action (form submissions)
        elif action == "data_exchange":
            form_data = decrypted_data.get("data", {})
            
            if current_screen == "PERSONAL_INFO":
                # Process travel details
                trip_details = process_trip_details(form_data)
                response = {
                    "data": trip_details
                }
                
            elif current_screen == "DETAILS":
                # Process personal details and validate
                validation_result = validate_personal_details(form_data)
                if validation_result["valid"]:
                    response = {
                        "data": {
                            "validation": "success"
                        }
                    }
                else:
                    response = {
                        "data": {
                            "validation": "failed",
                            "errors": validation_result["errors"]
                        }
                    }
                    
            elif current_screen == "PAYMENT":
                # Process payment and complete booking
                booking_result = process_booking(form_data, flow_token)
                response = {
                    "data": {
                        "booking_confirmation": booking_result
                    }
                }
            else:
                response = {"data": {}}
                
        # Handle BACK navigation
        elif action == "BACK":
            # You can update data when user goes back
            response = {
                "data": {
                    "message": "Navigated back successfully"
                }
            }
            
        else:
            # Default response for unhandled cases
            response = {
                "data": {},
                "error_message": "Unknown action or screen"
            }

        # Encrypt and return response
        encrypted_response = Security.encrypt_response(
            response=response, aes_key=aes_key, iv=iv
        )
        
        return Response(
            content=encrypted_response,
            media_type="text/plain",
            status_code=status.HTTP_200_OK,
        )
        
    except Exception as e:
        print(f"Error processing flow data: {str(e)}")
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Helper functions for your business logic
def get_available_time_slots(route, date, passengers):
    """Fetch available time slots from your database/service."""
    # Example implementation
    slots = [
        {"id": "04_08_2025$08_00", "title": "04-08-2025 at 08:00"},
        {"id": "04_08_2025$12_00", "title": "04-08-2025 at 12:00"},
        {"id": "04_08_2025$16_00", "title": "04-08-2025 at 16:00"},
        {"id": "04_08_2025$20_00", "title": "04-08-2025 at 20:00"},
    ]
    
    # Filter based on your business logic
    # available_slots = query_database(route, date, passengers)
    
    return slots


def get_seat_categories():
    """Get available seat categories with pricing."""
    return [
        {"id": "economy", "title": "🌟 Economy Class", "price": 50000},
        {"id": "vip", "title": "💺 VIP Class", "price": 75000},
        {"id": "first_class", "title": "👑 First Class", "price": 100000}
    ]


def process_trip_details(form_data):
    """Process and validate trip details."""
    print(f"Processing trip details: {form_data}")
    
    # Your validation logic here
    trip_type = form_data.get("trip_type")
    going_route = form_data.get("going_route")
    
    # Return processed data
    return {
        "processed": True,
        "trip_summary": f"{trip_type} trip on {going_route}"
    }


def validate_personal_details(form_data):
    """Validate personal details form."""
    errors = []
    
    # Example validation
    if not form_data.get("email input"):
        errors.append("Email is required")
    
    if not form_data.get("phone input"):
        errors.append("Phone number is required")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def process_booking(form_data, flow_token):
    """Process the final booking."""
    # Create booking in your system
    booking_id = create_booking_in_database(form_data, flow_token)
    
    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "message": "Your booking has been confirmed!"
    }


def create_booking_in_database(form_data, flow_token):
    """Create booking record in your database."""
    # Your database logic here
    # booking = Booking.create(...)
    return "BK12345"  # Return booking ID


def initialize_flow_session(flow_token):
    """Initialize flow session data."""
    # Store session data in your database or cache
    session_data = {
        "flow_token": flow_token,
        "created_at": datetime.now(),
        "status": "initialized",
        "user_data": {}
    }
    
    # Save to database/cache
    # SessionStore.create(flow_token, session_data)
    print(f"Flow session initialized: {flow_token}")
    
    return session_data




@app.post("/webhook")
async def webhook(request: Request) -> Dict:
    """
    Handle incoming WhatsApp webhook events.

    Args:
        request (Request): FastAPI request object containing webhook data.

    Returns:
        Dict: Response indicating the action taken or error details.

    Raises:
        HTTPException: If webhook processing fails.
    """
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

# I want to create a button that gives a user language choice the select a given flow 
import random

def get_mocked_language_choice():
    return random.choice(["swahili", "english"])






@app.post("/send-buttons")
async def buttons(to: str = Query(..., description="Recipient's WhatsApp number")):
    # Step 1: Properly validate phone number (e.g., must be digits only and correct length)
    if not to.isdigit() or len(to) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    recipient = to

    # Step 2: Send the language selection prompt (button template)
    await send_language_selection_prompt(to=recipient,text="Please select a language\nTatadhali chagua Lugha")

    # Step 3: Wait for a language selection (here we mock it)
    language = get_mocked_language_choice()

    # Step 4: Trigger the flow based on selected language
    return await trigger_language_flow(language, recipient)


     

@app.get("/send-language-choice")
async def trigger_language_flow(
    language: str = Query(..., description="Language choice (english/swahili)"),
    recipient: str = Query(..., description="Recipient's WhatsApp number")
) -> Dict:
    """
    Trigger a WhatsApp flow message based on language selection.

    Args:
        language (str): Language choice ("english" or "swahili").
        recipient (str): Recipient's WhatsApp number with country code.

    Returns:
        Dict: JSON response from the WhatsApp API.

    Raises:
        HTTPException: If the language is invalid or the flow message fails.
    """
    language = language.lower()
    
    if language not in flow_config:
        raise HTTPException(
            status_code=400,
            detail="Invalid language parameter. Choose 'english' or 'swahili'"
        )

    try:
        return await send_flow_message(
            to=recipient,
            flow_name=flow_config[language]["flow_name"],
            flow_id=flow_config[language]["flow_id"],
            flow_token=flow_config["token"]
        )
    except Exception as e:
        # logger.error(f"Error sending {language} flow message: {str(e)}")
        print("Exception:", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send {language} flow message"
        )



@app.post("/flow-callback")
async def handle_flow_submission(request: Request):
    data = await request.json()

    # Extract user payload from flow
    payload = data.get("payload")
    if not payload:
        return {"error": "Missing payload"}

    # Auto-fill travel date (e.g., tomorrow)
    travel_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Simulate storing or processing booking
    booking_info = {
        **payload,
        "travel_date": travel_date
    }

    # Log the booking or save to DB here
    print("Booking received:", booking_info)

    return {
        "status": "success",
        "message": "Booking received successfully",
        "booking_details": booking_info
    }        