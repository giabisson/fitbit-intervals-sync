import sys
import json
import requests
from urllib.parse import urlparse, parse_qs, urlencode
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
]

def get_oauth_config():
    with open("credentials.json") as f:
        cs = json.load(f)
    client_type = list(cs.keys())[0]
    config = cs[client_type]
    client_id = config["client_id"]
    client_secret = config["client_secret"]
    auth_uri = config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    token_uri = config.get("token_uri", "https://oauth2.googleapis.com/token")
    redirect_uri = config.get("redirect_uris", ["https://www.google.com"])[0]
    return client_id, client_secret, auth_uri, token_uri, redirect_uri

def generate_auth_url():
    client_id, _, auth_uri, _, redirect_uri = get_oauth_config()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{auth_uri}?{urlencode(params)}"

def exchange_code_for_token(code_or_url):
    client_id, client_secret, _, token_uri, redirect_uri = get_oauth_config()

    if "code=" in code_or_url:
        parsed = urlparse(code_or_url)
        code = parse_qs(parsed.query).get("code", [code_or_url])[0]
    else:
        code = code_or_url.strip()

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    res = requests.post(token_uri, data=payload)
    if not res.ok:
        print(f"\nERROR exchanging code for token ({res.status_code}): {res.text}")
        print("\nNote: Authorization codes expire quickly and can only be used once.")
        print("Please open the authorization URL below to get a fresh code:\n")
        print(generate_auth_url())
        return False

    token_data = res.json()
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("\nSUCCESS: Authorization complete! Token saved to token.json.")
    return True

def main():
    if len(sys.argv) > 1:
        auth_input = sys.argv[1]
        if exchange_code_for_token(auth_input):
            return

    auth_url = generate_auth_url()
    print("\n==========================================")
    print("GOOGLE HEALTH API - OAUTH AUTHORIZATION")
    print("==========================================")
    print("\nPlease open the following URL in your browser:\n")
    print(auth_url)
    print("\nAfter approving access, Google will redirect you to google.com.")
    print("Copy the full URL from your browser address bar (or the 'code' parameter).\n")

    user_input = input("Enter redirected URL or auth code: ").strip()
    exchange_code_for_token(user_input)

if __name__ == "__main__":
    main()
