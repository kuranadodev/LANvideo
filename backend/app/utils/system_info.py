import psutil


def get_system_info() -> dict:
    return {"cpu_percent": psutil.cpu_percent(interval=None), "memory_percent": psutil.virtual_memory().percent}
