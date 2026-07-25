import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://intervals.icu/api/v1"

class IntervalsClient:
    def __init__(self, api_key=None, athlete_id="me"):
        self.api_key = api_key or os.getenv("INTERVALS_API_KEY")
        if not self.api_key:
            raise ValueError("INTERVALS_API_KEY missing from environment or parameters.")
        self.athlete_id = athlete_id
        self.auth = ("API_KEY", self.api_key)

    def get_athlete_profile(self):
        """Fetches profile for authenticated athlete."""
        url = f"{BASE_URL}/athlete/{self.athlete_id}"
        res = requests.get(url, auth=self.auth)
        if res.ok:
            return res.json()
        print(f"Error fetching Intervals profile: {res.status_code} - {res.text}")
        return None

    def get_wellness(self, date_str):
        """Fetches wellness record for a specific date (YYYY-MM-DD)."""
        url = f"{BASE_URL}/athlete/{self.athlete_id}/wellness/{date_str}"
        res = requests.get(url, auth=self.auth)
        if res.ok:
            return res.json()
        print(f"Error fetching wellness for {date_str}: {res.status_code} - {res.text}")
        return None

    def update_wellness(self, date_str, wellness_data):
        """
        Updates wellness record for a specific date (YYYY-MM-DD).
        wellness_data is a dict with fields like restingHR, sleepSecs, weight, hrv, spO2, steps, etc.
        """
        url = f"{BASE_URL}/athlete/{self.athlete_id}/wellness/{date_str}"
        res = requests.put(url, auth=self.auth, json=wellness_data)
        if res.ok:
            print(f"Successfully updated Intervals.icu wellness for {date_str}: {wellness_data}")
            return res.json()
        print(f"Error updating wellness for {date_str}: {res.status_code} - {res.text}")
        return None

    def update_wellness_bulk(self, wellness_records):
        """
        Updates multiple wellness records. Each record in wellness_records must include an 'id' field (YYYY-MM-DD).
        """
        url = f"{BASE_URL}/athlete/{self.athlete_id}/wellness-bulk"
        res = requests.put(url, auth=self.auth, json=wellness_records)
        if res.ok:
            print(f"Successfully updated bulk wellness records ({len(wellness_records)} days).")
            return True
        print(f"Error updating bulk wellness: {res.status_code} - {res.text}")
        return False

if __name__ == "__main__":
    client = IntervalsClient()
    profile = client.get_athlete_profile()
    print("Athlete Profile:", profile.get("name") if profile else "Failed")
