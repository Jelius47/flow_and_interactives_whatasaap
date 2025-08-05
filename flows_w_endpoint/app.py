import os
from flask import Flask, request, Response
import hmac
import hashlib
from encryption import decrypt_request, encrypt_response, FlowEndpointException  # Hypothetical module

app = Flask(__name__)

# Environment variables
APP_SECRET = os.getenv("APP_SECRET")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
PASSPHRASE = os.getenv("PASSPHRASE", "")
PORT = int(os.getenv("PORT", 3000))

def is_request_signature_valid(request):
    if not APP_SECRET:
        print("App Secret is not set up. Please add your app secret in .env file to check for request validation")
        return True

    signature_header = request.headers.get("x-hub-signature-256", "")
    if not signature_header.startswith("sha256="):
        print("Error: Invalid signature header format")
        return False

    signature = signature_header.replace("sha256=", "")
    signature_bytes = signature.encode("utf-8")

    raw_body = request.get_data(as_text=True)
    hmac_obj = hmac.new(APP_SECRET.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256)
    digest = hmac_obj.hexdigest().encode("utf-8")

    return hmac.compare_digest(digest, signature_bytes)

@app.route("/", methods=["POST"])
async def handle_post():
    if not PRIVATE_KEY:
        raise ValueError('Private key is empty. Please check your env variable "PRIVATE_KEY".')

    if not is_request_signature_valid(request):
        # Return status code 432 if request signature does not match
        return Response(status=432)

    try:
        decrypted_request = decrypt_request(request.get_json(), PRIVATE_KEY, PASSPHRASE)
    except FlowEndpointException as err:
        print(f"Error: {err}")
        return Response(status=err.status_code)
    except Exception as err:
        print(f"Error: {err}")
        return Response(status=500)

    aes_key_buffer, initial_vector_buffer, decrypted_body = decrypted_request
    print("💬 Decrypted Request:", decrypted_body)

    # TODO: Uncomment and implement flow token validation
    # if not is_valid_flow_token(decrypted_body.get("flow_token")):
    #     error_response = {"error_msg": "The message is no longer available"}
    #     return Response(
    #         encrypt_response(error_response, aes_key_buffer, initial_vector_buffer),
    #         status=427
    #     )

    from flow import get_next_screen
    screen_response = await get_next_screen(decrypted_body)
    print("👉 Response to Encrypt:", screen_response)

    encrypted_response = encrypt_response(screen_response, aes_key_buffer, initial_vector_buffer)
    return Response(encrypted_response)

@app.route("/", methods=["GET"])
def handle_get():
    return "<pre>Nothing to see here.\nCheckout README.md to start.</pre>"

if __name__ == "__main__":
    app.run(port=PORT)
    print(f"Server is listening on port: {PORT}")