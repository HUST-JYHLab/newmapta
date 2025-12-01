import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import appdirs
from pathlib import Path

def load_processed_set() -> Dict[str, Any]:
    path = Path("logs/processed_challenges.json")
    if not path.exists():
        return {"processed_codes": [], "processed_urls": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        codes = data.get("processed_codes", [])
        urls = data.get("processed_urls", [])
        return {"processed_codes": list(codes), "processed_urls": list(urls)}
    except Exception:
        return {"processed_codes": [], "processed_urls": []}

def save_processed_set(processed: Dict[str, Any]):
    Path("logs").mkdir(parents=True, exist_ok=True)
    path = Path("logs/processed_challenges.json")
    safe = {
        "schema_version": 1,
        "processed_codes": list(set(processed.get("processed_codes", []))),
        "processed_urls": list(set(processed.get("processed_urls", []))),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)

def load_failure_counts() -> Dict[str, Any]:
    """加载题目失败计数（按 code 与 url 维度）。"""
    Path("logs").mkdir(parents=True, exist_ok=True)
    path = Path("logs/failure_counts.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        by_code = data.get("by_code", {})
        by_url = data.get("by_url", {})
        # 统一为字符串键，整型值
        by_code = {str(k): int(v) for k, v in by_code.items()}
        by_url = {str(k): int(v) for k, v in by_url.items()}
        return {"by_code": by_code, "by_url": by_url}
    except Exception:
        return {"by_code": {}, "by_url": {}}

def save_failure_counts(counts: Dict[str, Any]):
    """保存题目失败计数。"""
    Path("logs").mkdir(parents=True, exist_ok=True)
    path = Path("logs/failure_counts.json")
    safe = {
        "schema_version": 1,
        "by_code": {str(k): int(v) for k, v in counts.get("by_code", {}).items()},
        "by_url": {str(k): int(v) for k, v in counts.get("by_url", {}).items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)

def is_in_last_hour_of_competition(now: datetime | None = None) -> bool:
    """判断当前时间是否处于比赛时段的最后1小时。
    比赛时段：每天 10:00-13:00、15:00-18:00；最后1小时分别为 12:00-13:00、17:00-18:00。
    使用系统本地时间，无时区换算。
    """
    if now is None:
        now = datetime.now()# + timedelta(hours=10)
    hour = now.hour
    # 最后小时段的开始小时
    return hour in (11, 12, 16, 17)


def parse_targets_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def format_duration(elapsed_ms: float) -> str:
    """将耗时格式化为更友好的单位。
    - <1000ms: 使用毫秒
    - <60s: 使用秒，保留两位小数
    - >=60s: 使用 分秒（分钟为整数，秒保留一位小数）
    - >=60min: 使用 小时分秒（秒为整数）
    """
    try:
        total_ms = max(0, float(elapsed_ms))
    except Exception:
        return f"{elapsed_ms}ms"

    if total_ms < 1000:
        return f"{total_ms:.0f}ms"

    total_seconds = total_ms / 1000.0
    if total_seconds < 60:
        return f"{total_seconds:.2f}s"

    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    if minutes < 60:
        return f"{minutes}分{seconds:.1f}秒"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}小时{minutes}分{seconds:.0f}秒"



def get_embedder_config_from_env() -> Dict:
    host = os.getenv("CREWAI_EMBEDDING_BASE_URL", "").strip()
    model = os.getenv("CREWAI_EMBEDDING_MODEL", "nomic-embed-text").strip()
    if not host:
        return None
    return {
        "provider": os.getenv("CREWAI_EMBEDDING_MODEL_PROVIDER", "ollama"),
        "config": {
            "api_base": host,
            "model_name": model,
            "api_key": os.getenv("CREWAI_EMBEDDING_API_KEY", "").strip(),
        },
    }

def get_db_storage_path(storage_dir: str = None) -> str:
    """Returns the path for SQLite database storage.

    Returns:
        str: Full path to the SQLite database file
    """
    app_name = storage_dir or Path.cwd().name
    app_author = "CrewAI"

    data_dir = Path(appdirs.user_data_dir(app_name, app_author))
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)