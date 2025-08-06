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



# =============================================================================LETS START FROM HERE==============================================


@app.post("/register-encryption")
async def register():
    return await register_business_encryption()
""" THIS DID NOT WORK WELL THEN I HAD TO USE curl-x POST\ FILE WHICH RESEMBLED META DOCUMENTATION """




@app.post("/flow-data")
async def flow_data(request: Request):
    """Flow data exchange endpoint for booking system."""
    try:
        # Load and decrypt incoming data
        data = await request.json()
        encrypted_flow_data = data.get("encrypted_flow_data")
        encrypted_aes_key = data.get("encrypted_aes_key")
        initial_vector = data.get("initial_vector")

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
                "screen": None,
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
            
            initialize_flow_session(flow_token)
            
            response = {
                "screen": "PERSONAL_INFO",
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

        # Handle data_exchange actions
        if action == "data_exchange":
            form_data = decrypted_data.get("data", {})
            
            if current_screen == "PERSONAL_INFO":
                # Validate form data
                errors = validate_travel_details(form_data)
                if errors:
                    response = {
                        "screen": "PERSONAL_INFO",
                        "data": {
                            "validation": "failed",
                            "errors": errors
                        }
                    }
                else:
                    # Fetch availability slots
                    trip_type = form_data.get("trip_type")
                    going_route = form_data.get("going_route")
                    going_no_passengers = int(form_data.get("going_no_passengers"))
                    going_date = form_data.get("going_date")
                    return_route = form_data.get("return_route")
                    return_no_passengers = int(form_data.get("return_no_passengers")) if form_data.get("return_no_passengers") else None
                    return_date = form_data.get("return_date")
                    
                    if trip_type == "round_trip":
                        availability_data = get_available_time_slots_round(
                            going_route=going_route,
                            going_date=going_date,
                            going_no_passengers=going_no_passengers,
                            return_route=return_route,
                            return_date=return_date,
                            return_no_passengers=return_no_passengers
                        )
                    else:
                        availability_data = {
                            "going_availability_slots": get_available_time_slots(
                                route=going_route,
                                date=going_date,
                                passengers=going_no_passengers
                            ),
                            "return_availability_slots": []
                        }
                    
                    # Store form data in session
                    update_flow_session(flow_token, {"travel_details": form_data})
                    
                    response = {
                        "screen": "AVAILABILITY",
                        "data": availability_data
                    }
                
            elif current_screen == "AVAILABILITY":
                # Validate and store time selections
                going_time = form_data.get("going_time")
                return_time = form_data.get("return_time")
                
                errors = []
                if not going_time:
                    errors.append("Going time is required")
                if form_data.get("trip_type") == "round_trip" and not return_time:
                    errors.append("Return time is required")
                
                if errors:
                    response = {
                        "screen": "AVAILABILITY",
                        "data": {
                            "validation": "failed",
                            "errors": errors
                        }
                    }
                else:
                    # Store time selections in session
                    update_flow_session(flow_token, {"time_selections": form_data})
                    
                    # Fetch seat categories
                    seat_categories = get_seat_categories()
                    response = {
                        "screen": "SEATS",
                        "data": {
                            "seat_categories": seat_categories
                        }
                    }
                
            elif current_screen == "SEATS":
                # Validate seat class and passenger counts
                seat_class = form_data.get("seat_class")
                adult_passengers = int(form_data.get("adult_passengers")) if form_data.get("adult_passengers") else 0
                child_passengers = int(form_data.get("child_passengers")) if form_data.get("child_passengers") else 0
                
                # Retrieve travel details from session
                session_data = get_flow_session(flow_token)
                travel_details = session_data.get("travel_details", {})
                going_no_passengers = int(travel_details.get("going_no_passengers", 0))
                return_no_passengers = int(travel_details.get("return_no_passengers", 0)) if travel_details.get("return_no_passengers") else 0
                
                errors = []
                if not seat_class:
                    errors.append("Seat class is required")
                total_passengers = adult_passengers + child_passengers
                if total_passengers != going_no_passengers:
                    errors.append(f"Total adult and child passengers ({total_passengers}) must match going passengers ({going_no_passengers})")
                if travel_details.get("trip_type") == "round_trip" and total_passengers != return_no_passengers:
                    errors.append(f"Total adult and child passengers ({total_passengers}) must match return passengers ({return_no_passengers})")
                
                if errors:
                    response = {
                        "screen": "SEATS",
                        "data": {
                            "validation": "failed",
                            "errors": errors
                        }
                    }
                else:
                    # Store seat selections in session
                    update_flow_session(flow_token, {"seat_selections": form_data})
                    
                    response = {
                        "screen": "DETAILS",
                        "data": {
                            "validation": "success"
                        }
                    }
                
            elif current_screen == "DETAILS":
                # Validate personal details
                validation_result = validate_personal_details(form_data)
                if validation_result["valid"]:
                    # Store personal details in session
                    update_flow_session(flow_token, {"personal_details": form_data})
           
                    response = {
                        "screen": "PAYMENT",
                        "data": {
                            "booking_confirmation": 
                        {
                            "booking_id": "7436rjfd",
                            "status": "paid",
                            "message": "Thanks"

                        }
                        }
                    }
                else:
                    response = {
                        "screen": "DETAILS",
                        "data": {
                            "booking_confirmation": {
                                "booking_id": "7436rjfd",
                                "status": "failed",
                                "message":  validation_result["errors"]
                            },
                            
                        }
                    }
                
            elif current_screen == "PAYMENT":
                # Process payment and complete booking
                booking_result = process_booking(form_data, flow_token)
                response = {
                    "screen": "SUCCESS",
                    "data": {
                        "booking_confirmation": booking_result
                    }
                }
                
            else:
                response = {
                    "screen": current_screen,
                    "data": {
                        "error_message": "Unknown screen"
                    }
                }
                
        # Handle BACK navigation
        elif action == "BACK":
            previous_screen = get_previous_screen(current_screen)
            response = {
                "screen": previous_screen,
                "data": {
                    "message": "Navigated back successfully"
                }
            }
            
        else:
            response = {
                "screen": current_screen,
                "data": {
                    "error_message": "Unknown action"
                }
            }

        # Encrypt and return response
        print(f"Response before encryption: {response}")
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

# Helper functions for business logic
def get_available_time_slots(route, date, passengers):
    """Fetch available time slots for one-way trip."""
    slots = [
        {"id": f"{date.replace('-', '_')}$08_00", "title": f"{date} at 08:00"},
        {"id": f"{date.replace('-', '_')}$12_00", "title": f"{date} at 12:00"},
        {"id": f"{date.replace('-', '_')}$16_00", "title": f"{date} at 16:00"},
        {"id": f"{date.replace('-', '_')}$20_00", "title": f"{date} at 20:00"},
    ]
    # Filter based on route and passengers (implement actual database query here)
    return slots

def get_available_time_slots_round(going_route, going_date, going_no_passengers, return_route, return_date, return_no_passengers):
    """Fetch available time slots for round trip."""
    going_slots = get_available_time_slots(going_route, going_date, going_no_passengers)
    return_slots = get_available_time_slots(return_route, return_date, return_no_passengers)
    return {
        "going_availability_slots": going_slots,
        "return_availability_slots": return_slots
    }

def get_seat_categories():
    """Get available seat categories with pricing."""
    return [
        {"id": "economy", "title": "🌟 Economy Class price: 50000"},
        {"id": "vip", "title": "💺 VIP Class price: 75000"},
        {"id": "first_class", "title": "👑 First Class price: 100000"}
    ]

def validate_travel_details(form_data):
    """Validate travel details form."""
    errors = []
    if not form_data.get("trip_type"):
        errors.append("Trip type is required")
    if not form_data.get("going_route"):
        errors.append("Going route is required")
    if not form_data.get("going_no_passengers"):
        errors.append("Number of going passengers is required")
    if not form_data.get("going_date"):
        errors.append("Going date is required")
    if form_data.get("trip_type") == "round_trip":
        if not form_data.get("return_route"):
            errors.append("Return route is required")
        if not form_data.get("return_no_passengers"):
            errors.append("Number of return passengers is required")
        if not form_data.get("return_date"):
            errors.append("Return date is required")
    return errors

def validate_personal_details(form_data):
    """Validate personal details form."""
    errors = []
    if not form_data.get("full_name"):
        errors.append("Full name is required")
    if not form_data.get("email_input"):
        errors.append("Email is required")
    if not form_data.get("phone_input"):
        errors.append("Phone number is required")
    if not form_data.get("id_number"):
        errors.append("ID/Passport number is required")
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def process_booking(form_data, flow_token):
    """Process the final booking."""
    booking_id = create_booking_in_database(form_data, flow_token)
    return {
        "booking_id": booking_id,
        "status": "confirmed",
        "message": "Your booking has been confirmed!"
    }

def create_booking_in_database(form_data, flow_token):
    """Create booking record in your database."""
    # Implement actual database logic here
    return "BK12345"

def initialize_flow_session(flow_token):
    """Initialize flow session data."""
    session_data = {
        "flow_token": flow_token,
        "created_at": datetime.now(),
        "status": "initialized",
        "user_data": {}
    }
    # Save to database/cache (implement actual storage)
    print(f"Flow session initialized: {flow_token}")
    return session_data

def update_flow_session(flow_token, data):
    """Update session data with new information."""
    session_data = get_flow_session(flow_token)
    session_data["user_data"].update(data)
    # Save to database/cache (implement actual storage)
    print(f"Updated session for token {flow_token}: {session_data}")
    return session_data

def get_flow_session(flow_token):
    """Retrieve session data."""
    # Implement actual retrieval from database/cache
    return {
        "flow_token": flow_token,
        "created_at": datetime.now(),
        "status": "initialized",
        "user_data": {}
    }

def get_previous_screen(current_screen):
    """Determine the previous screen based on routing model."""
    routing = {
        "PERSONAL_INFO": None,
        "AVAILABILITY": "PERSONAL_INFO",
        "SEATS": "AVAILABILITY",
        "DETAILS": "SEATS",
        "PAYMENT": "DETAILS"
    }
    return routing.get(current_screen, None)


# ==================================== END OF FLOW WITH ENDPOINT IMPLEMENTATION ======================

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