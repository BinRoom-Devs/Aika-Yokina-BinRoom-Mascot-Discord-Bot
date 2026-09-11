import datetime

start_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
bot_status_text: str = "Offline"
bot_presence_status: str = "dnd"
bot_activity: str = "Nemenin BinRoom"
latency_ms: int = 0
guild_count: int = 1
latest_logs: list[str] = []


def log_event(message: str):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
    formatted_entry = f"{timestamp} {message}"
    print(formatted_entry)
    latest_logs.append(formatted_entry)
    if len(latest_logs) > 50:
        latest_logs.pop(0)

def get_uptime() -> str:
    delta = datetime.datetime.now(datetime.timezone.utc) - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"