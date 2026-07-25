import os
import argparse
from datetime import datetime, timedelta, timezone
from google_health_client import GoogleHealthClient
from intervals_client import IntervalsClient

def format_date_dict(d_dict):
    """Formats Google API Date object dict to YYYY-MM-DD string."""
    if not d_dict:
        return None
    year = d_dict.get("year")
    month = d_dict.get("month")
    day = d_dict.get("day")
    if year and month and day:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None

class FitbitIntervalsSync:
    def __init__(self):
        self.gh_client = GoogleHealthClient(prompt_auth=False)
        self.intervals_client = IntervalsClient()

    def fetch_daily_metrics_for_date(self, target_date_str):
        """
        Fetches Google Health API metrics for target_date_str (YYYY-MM-DD)
        and builds an Intervals.icu Wellness dictionary.
        """
        wellness = {}

        # 1. Daily Resting Heart Rate
        rhr_data = self.gh_client.list_data_points("daily-resting-heart-rate")
        if rhr_data and "dataPoints" in rhr_data:
            for dp in rhr_data["dataPoints"]:
                rhr_obj = dp.get("dailyRestingHeartRate", {})
                d_str = format_date_dict(rhr_obj.get("date"))
                if d_str == target_date_str or not d_str:
                    bpm = rhr_obj.get("beatsPerMinute")
                    if bpm:
                        try:
                            wellness["restingHR"] = int(float(bpm))
                        except ValueError:
                            pass

        # 2. Daily Heart Rate Variability (rMSSD in ms)
        hrv_data = self.gh_client.list_data_points("daily-heart-rate-variability")
        if hrv_data and "dataPoints" in hrv_data:
            for dp in hrv_data["dataPoints"]:
                hrv_obj = dp.get("dailyHeartRateVariability", {})
                d_str = format_date_dict(hrv_obj.get("date"))
                if d_str == target_date_str or not d_str:
                    rmssd = hrv_obj.get("averageHeartRateVariabilityMilliseconds") or \
                            hrv_obj.get("deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds")
                    if rmssd is not None:
                        wellness["hrv"] = round(float(rmssd), 2)

        # 3. Weight (kg)
        weight_data = self.gh_client.list_data_points("weight")
        if weight_data and "dataPoints" in weight_data:
            for dp in weight_data["dataPoints"]:
                w_obj = dp.get("weight", {})
                kg = w_obj.get("weightKg") or w_obj.get("weight")
                if kg is not None:
                    wellness["weight"] = round(float(kg), 2)

        # 4. Body Fat (%)
        bodyfat_data = self.gh_client.list_data_points("body-fat")
        if bodyfat_data and "dataPoints" in bodyfat_data:
            for dp in bodyfat_data["dataPoints"]:
                bf_obj = dp.get("bodyFat", {})
                pct = bf_obj.get("percentage")
                if pct is not None:
                    wellness["bodyFat"] = round(float(pct), 2)

        # 5. Sleep (duration, sleep score, sleep quality)
        sleep_data = self.gh_client.reconcile_data_points(
            "sleep",
            query_params={"filter": f'sleep.interval.civil_end_time >= "{target_date_str}"'}
        )
        if not sleep_data or "dataPoints" not in sleep_data:
            sleep_data = self.gh_client.list_data_points("sleep")

        if sleep_data and "dataPoints" in sleep_data:
            total_sleep_mins = 0
            explicit_sleep_score = None
            calculated_efficiency = None

            for dp in sleep_data["dataPoints"]:
                sleep_obj = dp.get("sleep", {})
                summary = sleep_obj.get("summary", {})
                
                score_val = sleep_obj.get("sleepScore") or summary.get("sleepScore") or \
                            sleep_obj.get("score") or summary.get("score")
                if score_val is not None:
                    explicit_sleep_score = float(score_val)

                mins_asleep = summary.get("minutesAsleep")
                mins_period = summary.get("minutesInSleepPeriod")

                if mins_asleep is not None:
                    total_sleep_mins += int(mins_asleep)
                    if mins_period and int(mins_period) > 0:
                        calculated_efficiency = (int(mins_asleep) / int(mins_period)) * 100.0

            if total_sleep_mins > 0:
                wellness["sleepSecs"] = total_sleep_mins * 60

            if explicit_sleep_score is not None:
                wellness["sleepScore"] = round(explicit_sleep_score, 1)
            elif calculated_efficiency is not None:
                wellness["sleepScore"] = round(calculated_efficiency, 1)

        # 6. Daily Oxygen Saturation (SpO2 %)
        spo2_data = self.gh_client.list_data_points("daily-oxygen-saturation")
        if spo2_data and "dataPoints" in spo2_data:
            for dp in spo2_data["dataPoints"]:
                spo2_obj = dp.get("dailyOxygenSaturation", {})
                d_str = format_date_dict(spo2_obj.get("date"))
                if d_str == target_date_str or not d_str:
                    avg_spo2 = spo2_obj.get("averagePercentage") or spo2_obj.get("percentage")
                    if avg_spo2 is not None:
                        wellness["spO2"] = round(float(avg_spo2), 2)

        # 7. Daily Respiratory Rate (breaths per minute)
        resp_data = self.gh_client.list_data_points("daily-respiratory-rate")
        if resp_data and "dataPoints" in resp_data:
            for dp in resp_data["dataPoints"]:
                resp_obj = dp.get("dailyRespiratoryRate", {})
                d_str = format_date_dict(resp_obj.get("date"))
                if d_str == target_date_str or not d_str:
                    rate = resp_obj.get("breathsPerMinute") or resp_obj.get("respiratoryRate")
                    if rate is not None:
                        wellness["respiration"] = round(float(rate), 2)

        # 8. VO2 Max
        vo2_data = self.gh_client.list_data_points("daily-vo2-max")
        if not vo2_data or "dataPoints" not in vo2_data:
            vo2_data = self.gh_client.list_data_points("vo2-max")
        if vo2_data and "dataPoints" in vo2_data:
            for dp in vo2_data["dataPoints"]:
                vo2_obj = dp.get("dailyVo2Max", {}) or dp.get("vo2Max", {})
                vo2_val = vo2_obj.get("vo2Max") or vo2_obj.get("value")
                if vo2_val is not None:
                    wellness["vo2max"] = round(float(vo2_val), 2)

        # 9. Steps
        steps_data = self.gh_client.list_data_points(
            "steps",
            query_params={"filter": f'steps.interval.civil_start_time >= "{target_date_str}T00:00:00"'}
        )
        if steps_data and "dataPoints" in steps_data:
            total_steps = 0
            for dp in steps_data["dataPoints"]:
                step_obj = dp.get("steps", {})
                count = step_obj.get("count")
                if count is not None:
                    total_steps += int(count)
            if total_steps > 0:
                wellness["steps"] = total_steps

        return wellness

    def sync_days(self, days=2, include_today=False):
        """
        Syncs health metrics for past finalized days (defaulting to yesterday and prior).
        If include_today is True, also syncs partial intraday data for today.
        """
        today = datetime.now().date()
        start_offset = 0 if include_today else 1
        end_offset = start_offset + days

        print(f"\nStarting sync for {days} finalized day(s) (include_today={include_today})...")

        synced_count = 0
        for offset in range(end_offset - 1, start_offset - 1, -1):
            date_obj = today - timedelta(days=offset)
            date_str = date_obj.strftime("%Y-%m-%d")
            print(f"\n--- Syncing date: {date_str} ---")

            wellness_data = self.fetch_daily_metrics_for_date(date_str)
            if not wellness_data:
                print(f"No Google Health data found for {date_str}.")
                continue

            print(f"Metrics gathered for {date_str}: {wellness_data}")
            result = self.intervals_client.update_wellness(date_str, wellness_data)
            if result:
                synced_count += 1

        print(f"\nSync complete! Successfully updated {synced_count} date(s) on Intervals.icu.")

def main():
    parser = argparse.ArgumentParser(description="Sync Fitbit data from Google Health API to Intervals.icu")
    parser.add_argument("--days", type=int, default=2, help="Number of past finalized days to sync (default: 2)")
    parser.add_argument("--include-today", action="store_true", help="Include partial intraday data for today")
    args = parser.parse_args()

    if not os.path.exists("token.json"):
        print("ERROR: token.json not found.")
        print("Please run authorization setup first by executing: python auth_setup.py")
        return

    sync = FitbitIntervalsSync()
    sync.sync_days(days=args.days, include_today=args.include_today)

if __name__ == "__main__":
    main()
