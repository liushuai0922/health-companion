from datetime import datetime, timedelta, timezone

# First local MVP uses the user's China Standard Time, not the server's OS timezone.
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


def local_today():
    return datetime.now(LOCAL_TIMEZONE).date()
