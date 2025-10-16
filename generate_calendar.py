import json
import jdatetime
from iranholidays import holiday_occasion

def is_jalali_leap(year):
    """Checks if a Jalali year is a leap year."""
    # This is a common algorithm for determining Jalali leap years.
    return (((((year - 474) % 2820) + 474) + 38) * 682) % 2816 < 682

def generate_iranian_calendar(start_year=1390, end_year=1410):
    """
    Generates a list of all days from start_year to end_year,
    marking official holidays and Fridays.
    """
    calendar_data = []

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if month <= 6:
                days_in_month = 31
            elif month <= 11:
                days_in_month = 30
            else: # Esfand
                days_in_month = 30 if is_jalali_leap(year) else 29

            for day in range(1, days_in_month + 1):
                try:
                    # Use jdatetime.date as expected by the iranholidays library
                    j_date = jdatetime.date(year, month, day)

                    holiday_desc = holiday_occasion(j_date)
                    is_friday = j_date.weekday() == 6

                    is_holiday = holiday_desc is not False
                    is_national_or_religious_holiday = is_holiday and not is_friday

                    calendar_entry = {
                        "date": j_date.strftime("%Y/%m/%d"),
                        "is_national_holiday": 1 if is_national_or_religious_holiday else 0,
                        "is_religious_holiday": 0,
                        "is_friday": 1 if is_friday else 0,
                        "description": holiday_desc if is_holiday else ""
                    }

                    if is_holiday and is_friday:
                        calendar_entry["is_national_holiday"] = 1

                    calendar_data.append(calendar_entry)
                except ValueError:
                    continue

    return calendar_data

if __name__ == "__main__":
    full_calendar = generate_iranian_calendar()
    # Use compact separators to reduce file size
    print(json.dumps(full_calendar, indent=None, separators=(',', ':'), ensure_ascii=False))