
import os
from dotenv import load_dotenv

load_dotenv()
access_token= os.getenv("ACCESS_TOKEN")
phone_number_id = os.getenv("PHONE_NUMBER_ID")
whatsapp_api_version=os.getenv("WHATSAPP_API_VERSION")

flow_config = {
        "english": {"flow_id": "713784581492733", "flow_name": "azam_v2"},
        "swahili": {"flow_id": "552112574623758", "flow_name": "azam_v1"},
        "flow_token": {"token":"flows-builder-b28d270e"}
    }
