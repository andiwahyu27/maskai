"""Date utilities"""
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

def build_jakarta_date_range(start_str, end_str):
    """Build timezone-aware half-open date range for queries"""
    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    if start_date > end_date:
        raise ValueError("Tanggal awal tidak boleh setelah tanggal akhir")
    start_dt = datetime.combine(start_date, time.min, tzinfo=JAKARTA_TZ)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=JAKARTA_TZ)
    return start_dt, end_dt
