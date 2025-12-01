import logging
import os
# from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def get_logger(tag: str, stream_handler: bool = True, log_dir: Path = None) -> logging.Logger:
    logger = logging.getLogger(f"{tag}")
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if not log_dir:
        if "." in tag:
            dir_name = tag.split(".")[0]
        else:
            dir_name = None
        log_dir = Path("logs") / datetime.now().strftime("%Y-%m-%d") 
        if dir_name:
            log_dir = log_dir / dir_name
    log_dir.mkdir(parents=True, exist_ok=True)
    # 处理控制台 handler：存在则更新格式；需要关闭则移除
    existing_streams = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
    if stream_handler:
        if not existing_streams:
            console = logging.StreamHandler()
            console.setFormatter(fmt)
            logger.addHandler(console)
    else:
        for h in existing_streams:
            logger.removeHandler(h)
    # 处理文件 handler：若路径不同则替换为当天路径
    desired_path = log_dir / f"{tag}.log"
    existing_files = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    need_new_file = True if not existing_files else False
    for h in existing_files:
        try:
            current_path = Path(getattr(h, "baseFilename"))
        except Exception:
            current_path = None
        if current_path == desired_path:
            need_new_file = False
        else:
            logger.removeHandler(h)
            need_new_file = True
    if need_new_file:
        fh = logging.FileHandler(desired_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger