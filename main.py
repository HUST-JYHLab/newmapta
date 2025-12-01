from dotenv import load_dotenv
load_dotenv()
import os, sys
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crewAI', 'lib', 'crewai', 'src'))
import urllib3
urllib3.disable_warnings()
import argparse
import logging
import time
import json
from hashlib import md5
from typing import List, Dict, Any
from lib.config import is_debug, set_debug, is_verbose, set_verbose
from lib.executor import run_batch_for_items

# import litellm
# # litellm.json_logs = False
# litellm.log_level = "DEBUG"
# litellm._turn_on_debug()


from lib.logger import get_logger
from lib.utils import load_processed_set, save_processed_set, load_failure_counts, save_failure_counts, is_in_last_hour_of_competition, parse_targets_from_file

# 引入 CTF 平台 API 接口
try:
    from ctf_api import fetch_ctf_challenges, submit_ctf_flag, get_ctf_hint
except Exception:
    get_logger("main").error("CTF API模块加载失败，将禁用CTF API相关功能")
    # 允许在无该模块时继续运行（仅禁用 API 功能）
    fetch_ctf_challenges = None
    submit_ctf_flag = None
    get_ctf_hint = None

# mcps = MCPServerStdio(
#             command="python",
#             args=["mcp_server.py"],
#             cache_tools_list=True,
#         )


def _filter_items(batch_items, failure_counts, last_hour, watch_mode, logger):
    """
    过滤失败次数超过阈值的题目，支持轮询和批量模式。
    """
    new_items = []
    for it in batch_items:
        code = str(it.get("code")) if it.get("code") is not None else None
        url = str(it.get("url"))
        c = failure_counts["by_code"].get(code, 0) if code else 0
        u = failure_counts["by_url"].get(url, 0)
        metric = c if watch_mode else max(c, u)
        threshold = 100
        if metric >= threshold:
            logger.info(f"跳过题目（已失败{metric}次）: {url}")
            continue
        if watch_mode:
            it["failure_counts"] = c
        new_items.append(it)
    return new_items

def _update_failure_counts(items, results, failure_counts):
    """
    根据结果更新失败计数，成功则清零，失败则+1。
    """
    for idx, it in enumerate(items):
        (_, flag_found, _) = results[idx]
        code = str(it.get("code")) if it.get("code") is not None else None
        url = str(it.get("url"))
        if flag_found:
            if code and code in failure_counts["by_code"]:
                del failure_counts["by_code"][code]
            if url in failure_counts["by_url"]:
                del failure_counts["by_url"][url]
        else:
            if code:
                failure_counts["by_code"][code] = failure_counts["by_code"].get(code, 0) + 1
            failure_counts["by_url"][url] = failure_counts["by_url"].get(url, 0) + 1

def _mark_processed(items, results, processed, mark_on_solve):
    """
    标记已处理题目。
    """
    for idx, it in enumerate(items):
        (_, flag_found, _) = results[idx]
        code = str(it.get("code")) if it.get("code") is not None else None
        url = str(it.get("url"))
        mark = (flag_found if mark_on_solve else True)
        if mark:
            if code:
                processed["processed_codes"].append(code)
            processed["processed_urls"].append(url)

def get_hexstrike_mcps_from_env() -> List[str]:
    """读取 HEXSTRIKE MCP 服务器 URL 并返回 mcps 列表。
    - 使用字符串引用形式，CrewAI 将自动连接该 MCP 服务器。
    - 如果未设置环境变量则返回空列表，表示不启用 MCP。
    """
    url = os.getenv("HEXSTRIKE_SERVER_URL", "").strip()
    if not url:
        return []
    # return [MCPServerHTTP(
    #     url=url,
    #     transport="streamable-http"
    # )]


def load_ctf_challenges_from_api(logger: logging.Logger) -> List[Dict[str, Any]]:
    """通过 CTF 平台 API 获取题目并提取 (url, code) 列表。
    支持不同字段名的兼容：
    - URL 字段：url/target_url/target/challenge_url；
    - 题目代码字段：code/challenge_code/id/challenge_id；
    - 兼容 target_info: { ip: str, port: List[int] }，当未提供显式 URL 时，从此结构生成 URL。

    生成 URL 规则：
    - 端口为 80 -> 使用 http://ip
    - 端口为 443 -> 使用 https://ip
    - 其他端口 -> 使用 http://ip:port

    若接口不可用或解析失败，返回空列表。
    """
    if fetch_ctf_challenges is None:
        logger.warning("CTF API模块不可用，跳过从平台获取题目。")
        return []
    try:
        raw = fetch_ctf_challenges()
        data = json.loads(raw or "{}")
        stage = data.get("current_stage")
        if stage == "debug" and not is_debug():
            logger.info("当前CTF平台为调试模式!")
            return []
        chals = data.get("challenges", []) or []
        total = len(chals)
        solved_count = 0
        diff_counts = {"easy": 0, "medium": 0, "hard": 0}
        normalized: List[Dict[str, Any]] = []
        for c in chals:
            # 统计信息
            difficulty = str(c.get("difficulty", "")).lower()
            if difficulty in diff_counts:
                diff_counts[difficulty] += 1
            if bool(c.get("solved", False)):
                solved_count += 1

            url = (
                c.get("url")
                or c.get("target_url")
                or c.get("target")
                or c.get("challenge_url")
            )
            code = (
                c.get("code")
                or c.get("challenge_code")
                or c.get("id")
                or c.get("challenge_id")
            )
            # 仅返回未解题目
            if bool(c.get("solved", False)) and not is_debug():
                # pass
                continue

            if url:
                normalized.append({
                    "url": str(url),
                    "code": code,
                    "difficulty": difficulty,
                    "hint_viewed": bool(c.get("hint_viewed", False)),
                })
                continue

            # 无显式 URL 时，尝试从 target_info 生成
            target_info = c.get("target_info")
            if isinstance(target_info, dict):
                ip = target_info.get("ip")
                ports = target_info.get("port")
                # 规范化端口为列表
                if isinstance(ports, int):
                    ports_list: List[int] = [ports]
                elif isinstance(ports, (list, tuple)):
                    # 仅保留整数端口
                    ports_list = [int(p) for p in ports if isinstance(p, (int, str)) and str(p).isdigit()]
                else:
                    ports_list = []

                candidate_urls: List[str] = []
                if ip:
                    if not ports_list:
                        # 未给端口，默认 http 80
                        candidate_urls.append(f"http://{ip}")
                    else:
                        for p in ports_list:
                            candidate_urls.append(f"http://{ip}:{p}")
                                

                # 去重并写入
                seen = set()
                for u in candidate_urls:
                    if u not in seen:
                        normalized.append({"url": u, "code": code, "difficulty": difficulty})
                        seen.add(u)

        # 按难度对未解题目排序：easy -> medium -> hard -> 其他
        rank = {"easy": 0, "medium": 1, "hard": 2}
        normalized.sort(key=lambda it: (rank.get(str(it.get("difficulty", "")).lower(), 99), str(it.get("code") or ""), str(it.get("url") or "")))

        # 输出统计信息
        if stage:
            logger.info(f"CTF平台阶段: {stage}")
        logger.info(
            f"题目总数: {total} | 已解: {solved_count} | 未解: {total - solved_count} | 难度分布: easy={diff_counts['easy']}, medium={diff_counts['medium']}, hard={diff_counts['hard']}"
        )
        logger.info(f"返回未解题目数(规范化后): {len(normalized)}")
        return normalized
    except Exception as e:
        logger.error(f"解析CTF平台题目失败: {e}")
        return []



def main():
    # 设置全局异常处理
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            print("\n👋 用户中断执行")
            return
        logger = get_logger("main")
        logger.critical("未处理的异常:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = global_exception_handler

    parser = argparse.ArgumentParser(description="CTF 执行器（CrewAI 版本）")
    parser.add_argument("--url", help="单个目标URL", default="")
    parser.add_argument("--targets", help="批量目标文件路径", default="targets.txt")
    parser.add_argument("--use_ctf_api", help="从CTF平台获取题目并批量执行", action="store_true")
    parser.add_argument("--auto_submit", help="发现flag后自动提交到CTF平台", action="store_true")
    parser.add_argument("--challenge_code", help="单目标模式下的题目代码（用于自动提交）", default="")
    parser.add_argument("--watch_ctf_api", help="循环从CTF平台检测新题并仅执行未做题目", action="store_true")
    parser.add_argument("--poll_interval", help="CTF平台轮询间隔秒数", type=int, default=30)
    parser.add_argument("--hint_last_hour",  default=True, help="仅在每个比赛时段的最后1小时为未解题目获取提示", action="store_true")
    parser.add_argument("--debug",  default=False, help="调试模式流程", action="store_true")
    parser.add_argument("--verbose",  default=False, help="verbose模式，输出更多信息", action="store_true")
    parser.add_argument("--max_concurrent",  default=1, help="最大并发执行数", type=int)

    args = parser.parse_args()

    if args.debug:
        set_debug(True)
    if args.verbose:
        set_verbose(True)

    # # 在后台线程中启动 MCP 服务器
    # def run_server():
    #     from mcp_server import run_mcp_server
    #     run_mcp_server()

    # print("[1/2] 正在启动 MCP 服务器...")
    # server_thread = threading.Thread(target=run_server, daemon=True)
    # server_thread.start()

    # # 等待服务器启动
    # time.sleep(3)
    # print("[2/2] MCP 服务器已启动，开始 CTF 解题...")
    # print()

    # 批量来源：优先从 CTF 平台获取；否则从文件读取
    base_logger = get_logger("main")

    if args.use_ctf_api and args.watch_ctf_api:
        if fetch_ctf_challenges is None:
            print("CTF平台模块不可用，无法启用轮询模式")
            return 1
        base_logger.info(f"进入CTF平台轮询模式，间隔 {args.poll_interval}s，标记规则: 尝试")
        processed = load_processed_set()
        failure_counts = load_failure_counts()
        while True:
            batch_items = load_ctf_challenges_from_api(base_logger)
            if not batch_items:
                base_logger.info("CTF平台暂无题目或解析失败，等待后重试...")
                time.sleep(args.poll_interval)
                continue
           
            new_items = _filter_items(batch_items, failure_counts, is_in_last_hour_of_competition(), True, base_logger)

            if not new_items:
                base_logger.info("可执行题目为空（均已失败≥3次），等待后重试...")
                time.sleep(args.poll_interval)
                continue

            base_logger.info(f"发现新题目: {len(new_items)}，开始执行...")
            results = run_batch_for_items(new_items, args)
            _update_failure_counts(new_items, results, failure_counts)
            _mark_processed(new_items, results, processed, False)
            save_failure_counts(failure_counts)
            save_processed_set(processed)
            base_logger.info("轮询周期结束，等待后继续...")
            time.sleep(args.poll_interval)
        # 不会到达此处
    else:
        # 单次批量：从平台或文件加载一次并执行
        batch_items: List[Dict[str, Any]] = []
        if args.use_ctf_api:
            batch_items = load_ctf_challenges_from_api(base_logger)
            if not batch_items:
                print("CTF平台未返回题目或解析失败，退出")
                return 1
        elif args.url:
            batch_items = [{"url": args.url, "code": md5(args.url.encode()).hexdigest()}]
        else:
            targets = parse_targets_from_file(args.targets)
            if not targets:
                print("未提供 --url 且未在文件中找到有效目标，退出")
                return 1
            batch_items = [{"url": t, "code": md5(t.encode()).hexdigest()} for t in targets]

    # 失败3次题目跳过过滤（单次批量模式）
    failure_counts = load_failure_counts()
    filtered_items = _filter_items(batch_items, failure_counts, is_in_last_hour_of_competition(), False, base_logger)

    if not filtered_items:
        print("可执行题目为空（均已失败≥10次），退出")
        return 1

    results_summary = run_batch_for_items(filtered_items, args)
    _update_failure_counts(filtered_items, results_summary, failure_counts)
    save_failure_counts(failure_counts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())