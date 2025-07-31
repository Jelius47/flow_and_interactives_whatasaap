
import os
from dotenv import load_dotenv

load_dotenv()
access_token= os.getenv("ACCESS_TOKEN")
phone_number_id = os.getenv("PHONE_NUMBER_ID")
whatsapp_api_version=os.getenv("WHATSAPP_API_VERSION")
