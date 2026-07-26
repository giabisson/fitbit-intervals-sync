import os
import json
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
]

CLIENT_SECRETS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
BASE_URL = "https://health.googleapis.com/v4"

class GoogleHealthClient:
    def __init__(self, client_secrets_file=CLIENT_SECRETS_FILE, token_file=TOKEN_FILE, prompt_auth=False):
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.creds = None
        self._authenticate(prompt_auth=prompt_auth)

    def _authenticate(self, prompt_auth=False):
        """Gets or creates OAuth 2.0 credentials."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    self.creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
            except Exception as e:
                print(f"Error loading {self.token_file}: {e}")
                self.creds = None

        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self._save_token()
                return
            except Exception as e:
                print(f"Failed to refresh token: {e}. Re-authenticating...")
                self.creds = None

        if not self.creds or not self.creds.valid:
            if not prompt_auth:
                raise PermissionError("Google OAuth credentials invalid or missing. Please run auth_setup.py.")

    def _save_token(self):
        """Saves authorized user credentials to token file."""
        if self.creds:
            with open(self.token_file, "w") as f:
                f.write(self.creds.to_json())

    def _get_headers(self):
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            self._save_token()
        return {
            "Authorization": f"Bearer {self.creds.token}",
            "Accept": "application/json",
        }

    def get_identity(self):
        """Fetches the user's identity details."""
        url = f"{BASE_URL}/users/me/identity"
        res = requests.get(url, headers=self._get_headers())
        if res.ok:
            return res.json()
        print(f"Error fetching identity: {res.status_code} - {res.text}")
        return None

    def list_data_points(self, data_type, query_params=None):
        """Fetches data points for a given dataType."""
        url = f"{BASE_URL}/users/me/dataTypes/{data_type}/dataPoints"
        res = requests.get(url, headers=self._get_headers(), params=query_params)
        if res.ok:
            return res.json()
        print(f"Error fetching data points for {data_type}: {res.status_code} - {res.text}")
        return None

    def reconcile_data_points(self, data_type, query_params=None):
        """Fetches reconciled data points for a given dataType."""
        url = f"{BASE_URL}/users/me/dataTypes/{data_type}/dataPoints:reconcile"
        res = requests.get(url, headers=self._get_headers(), params=query_params)
        if res.ok:
            return res.json()
        print(f"Error reconciling data points for {data_type}: {res.status_code} - {res.text}")
        return None

    def daily_rollup(self, data_type, year, month, day):
        """Aggregates data points for a single day via dailyRollUp endpoint."""
        url = f"{BASE_URL}/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp"
        body = {
            "range": {
                "start": {
                    "date": {"year": year, "month": month, "day": day},
                    "time": {"hours": 0, "minutes": 0, "seconds": 0}
                },
                "end": {
                    "date": {"year": year, "month": month, "day": day},
                    "time": {"hours": 23, "minutes": 59, "seconds": 59}
                }
            },
            "windowSizeDays": 1
        }
        res = requests.post(url, headers=self._get_headers(), json=body)
        if res.ok:
            return res.json()
        print(f"Error fetching dailyRollUp for {data_type}: {res.status_code} - {res.text}")
        return None

if __name__ == "__main__":
    client = GoogleHealthClient()
    identity = client.get_identity()
    print("User Identity:", identity)
