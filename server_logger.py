import logging
import os

loggers = {}  # Lưu trữ logger theo server ID

def get_logger(guild_id):
    """Trả về logger cho một server cụ thể"""
    log_filename = f"logs/{guild_id}.log"

    if guild_id in loggers:
        return loggers[guild_id]

    # Tạo thư mục nếu chưa có
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger(str(guild_id))
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(log_filename, encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    loggers[guild_id] = logger
    return logger
