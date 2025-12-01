import os, time, json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pebble import ProcessPool, ProcessExpired
from concurrent.futures import TimeoutError
import multiprocessing
import traceback
from lib.logger import get_logger
from lib.utils import format_duration, is_in_last_hour_of_competition, get_embedder_config_from_env, get_db_storage_path
from lib.config import is_debug, is_verbose

try:
    from ctf_api import fetch_ctf_challenges, submit_ctf_flag, get_ctf_hint
except Exception:
    # 允许在无该模块时继续运行（仅禁用 API 功能）
    fetch_ctf_challenges = None
    submit_ctf_flag = None
    get_ctf_hint = None

# 线程安全的memory_key_status
manager = multiprocessing.Manager()
memory_key_status: Dict[str, bool] = manager.dict() 
memory_lock = manager.Lock()

class CTFExecutor:
    def __init__(self, cdp_url: str = None):
        from lib.workflow import CTFOpportunisticWorkflow
        from lib.llm import CrewLLMConfig
        from lib.tools import setup_tools
        from lib.knowledge import get_knowledge
        # init_rag_countext()
        knowledge = get_knowledge()
        # 初始化系统
        self.system = CTFOpportunisticWorkflow(llm_config=CrewLLMConfig(), tools=setup_tools(cdp_url), knowledge=knowledge)
        self.logger = get_logger("executor")


    def parse_result(self, result: str, target_code: str, target_url: str, file_name: str, target_key: str) -> str:
        # 运行完成后，尽量只保留 flag 内容作为返回
        from lib.tools import FlagValidatorTool
        fv = FlagValidatorTool()
        validation = fv._run(str(result))
        flag_found = validation.startswith("✅ 发现有效Flag")
        flag_content = validation.split(":", 1)[1].strip() if flag_found else ""
        self.logger.info(f"CTF挑战完成，{target_code} - {target_url} {('发现Flag: ' + flag_content) if flag_found else '未找到flag'}")
        # 返回尽可能简化的结果：仅返回 flag 字符串（若未找到则返回原始结果以便排错）
        return flag_content if flag_found else result

    def _crew_step_callback(self, step_output):
        """CrewAI步骤回调，用于监控执行进度"""
        self.ailogger.info(f"步骤输出: {str(step_output)}")

    def execute_ctf(self, target_code: str, target_url: str, hint: str | None = None, failure_counts: int = 0):
        self.logger.info(f"🎯 开始CTF挑战: {target_code} - {target_url} - {hint} - {failure_counts}")
        embedder_conf = get_embedder_config_from_env()
        # 为每题设置独立的命名空间，避免记忆混淆
        target_key = f"ctf_{target_code}_{target_url.replace('://', '_').replace('/', '_')}"
        # os.environ["CREWAI_STORAGE_DIR"] = f"{target_key}"
        # 内部初始化
        from crewai import Crew, Process
        from crewai.memory.short_term.short_term_memory import ShortTermMemory
        from crewai.memory.entity.entity_memory import EntityMemory
        from crewai.memory.long_term.long_term_memory import LongTermMemory

        self.ailogger = get_logger(f"ai.{target_key}", False)
        
        if is_debug():
            worker_agents = self.system.create_debug_agents()
            manager_agent = self.system.create_debug_manager_agent()
            workflow = self.system.create_debug_workflow(target_url, target_code, hint)
        else:
            # 获取agents和工作流
            agents = self.system._get_opportunistic_agents()
            worker_agents = [agent for key, agent in agents.items() if key != "opportunistic_coordinator"]
            manager_agent = agents["opportunistic_coordinator"]
            workflow = self.system.create_opportunistic_workflow(target_url, target_code, hint)

        db_storage_path = get_db_storage_path(target_key)

        Path(f"logs/{datetime.now().strftime('%Y-%m-%d')}/crew").mkdir(parents=True, exist_ok=True)
        file_name = f"{datetime.now().strftime('%Y-%m-%d')}/crew/{target_code}_{target_url.replace('://', '_').replace('/', '_')}.log"
        try:
            stream=False
            # 创建分层crew
            crew = Crew(
                name=f"ctf_attack_{target_code}",
                output_log_file=f"logs/{file_name}",
                agents=worker_agents,
                tasks=workflow,
                stream=stream,
                process=Process.hierarchical,  # 关键改进：使用分层流程
                manager_agent=manager_agent,  # 协调器作为经理
                llm=self.system.llm_config.get_llm_by_role("opportunistic_coordinator"),
                # chat_llm=self.system.llm_config.get_llm_by_role("opportunistic_coordinator"),
                # function_calling_llm=self.system.llm_config.get_llm_by_role("tool_call"),
                verbose=is_verbose(),
                tracing=is_verbose(),
                memory=True,
                max_rpm=30,  # 更合理的限制
                max_iter=8,   # 给予更多推理空间
                max_execution_time=1700,  # 1800秒超时
                task_callback=self._crew_step_callback,  # 添加任务回调
                step_callback=self._crew_step_callback,  # 添加步骤回调
                # embedder=embedder_conf,
                long_term_memory=LongTermMemory(
                    path=f"{db_storage_path}/long_term_memory_storage.db"
                )
            )

            crew._short_term_memory = ShortTermMemory(
                crew=crew,
                embedder_config=embedder_conf,
                path=db_storage_path,
            )
            crew.short_term_memory = crew._short_term_memory
            crew._entity_memory = EntityMemory(
                crew=crew, embedder_config=embedder_conf, path=db_storage_path
            )
            crew.entity_memory = crew._entity_memory

        except Exception as e:
            self.logger.error(f"创建Crew失败: {e} {traceback.format_exc()}")
            return f"⚠️ 创建Crew失败: {e}"

        try:
            def _is_memory_initialized(target_key: str) -> bool:
                """线程安全地检查memory是否已初始化"""
                with memory_lock:
                    return memory_key_status.get(target_key, False)
            if not _is_memory_initialized(target_key):
                for command_type in ['short', 'long', 'entity']: # kickoff_outputs、knowledge 看情况
                    try:
                        crew.reset_memories(command_type=command_type)
                    except:
                        pass
                with memory_lock:
                    memory_key_status[target_key] = True
            result = crew.kickoff()
            if stream:
                for chunk in result:
                    pass
                try:
                    crew.reset_memories(command_type='long')      # Long-term memory
                except:
                    pass
                try:
                    crew.reset_memories(command_type='entity')    # Entity memory
                except:
                    pass
                # try:
                #     crew.reset_memories(command_type='knowledge') # Knowledge storage
                # except:
                #     pass
                with memory_lock:
                    memory_key_status[target_key] = True
            result = crew.kickoff()
            if stream:
                for chunk in result:
                    pass
                    # print(chunk.content, end="", flush=True)
                result = result.result
            self.logger.info(f"usage_metrics: {crew.usage_metrics}")
            return self.parse_result(result, target_code, target_url, file_name, target_key)
        except Exception as e:
            self.logger.error(f"kickoff 执行失败: {e} {traceback.format_exc()}")
            return f"⚠️ kickoff 异常: {e}"


class PebbleCTFExecutor:
    """精简的Pebble CTF执行器 - 修复序列化问题"""
    
    def __init__(self, cdp_urls: List[str] = None, max_concurrent: int = 2):
        self.cdp_urls = cdp_urls or [os.getenv("STEEL_CONNECT_URL", "ws://127.0.0.1:13001")]
        self.max_workers = min(len(self.cdp_urls), max_concurrent)
        
        # 使用简单的日志设置，避免传递复杂对象
        self.logger = get_logger("pebble")
        
        self.process_pool = ProcessPool(
            max_workers=self.max_workers,
            max_tasks=0,
            initializer=self._process_initializer
        )
        self.logger.info(f"Pebble执行器初始化完成 - 进程数: {self.max_workers}")

    def _process_initializer(self):
        """进程初始化"""
        pass
        # 在子进程中重新初始化日志
        # logging.basicConfig(
        #     level=logging.INFO,
        #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # )

    def run_batch_concurrently(self, batch_items: List[Dict[str, Any]], args) -> List[Tuple[str, bool, str]]:
        """并发执行批量任务 - 修复序列化问题"""
        self.logger.info(f"开始执行 {len(batch_items)} 个CTF任务")
        
        start_time = time.time()
        futures = {}
        results = []
        
        # 提交所有任务 - 只传递可序列化的数据
        for i, item in enumerate(batch_items):
            cdp_url = self.cdp_urls[i % len(self.cdp_urls)]
            challenge_code = item.get("code", f"unknown_{i}")
            
            # 准备可序列化的任务数据
            task_data = {
                'url': item['url'],
                'code': challenge_code,
                'failure_counts': item.get('failure_counts', 0),
                'cdp_url': cdp_url,
                'hint_last_hour': getattr(args, 'hint_last_hour', False)
            }
            
            future = self.process_pool.schedule(
                execute_single_task,  # 使用模块级函数，避免传递self
                args=(task_data,),    # 只传递可序列化数据
                timeout=1700
            )
            time.sleep(1)
            futures[future] = (i, item)
            self.logger.info(f"提交任务: {challenge_code} - {item['url']}")
        
        # 监控任务执行
        completed_count = 0
        total_tasks = len(futures)
        
        while futures and completed_count < total_tasks:
            finished_futures = []
            for future, task_info in list(futures.items()):
                if future.done():
                    finished_futures.append((future, task_info))
            
            for future, (i, item) in finished_futures:
                challenge_code = item.get("code", "unknown")
                
                try:
                    result = future.result()
                    results.append((i, result))
                    self.logger.info(f"任务完成: {challenge_code} - 结果: {'成功' if result[1] else '失败'}")
                    
                except (ProcessExpired, TimeoutError):
                    results.append((i, (item["url"], False, "执行超时")))
                    self.logger.warning(f"任务超时: {challenge_code}")
                    
                except Exception as e:
                    results.append((i, (item["url"], False, f"执行异常: {str(e)}")))
                    self.logger.error(f"任务异常: {challenge_code} - {e}")
                
                completed_count += 1
                del futures[future]
            
            # 进度更新
            if futures:
                # progress = (completed_count / total_tasks) * 100
                # self.logger.info(f"进度: {completed_count}/{total_tasks} ({progress:.1f}%)")
                time.sleep(5)
        
        # 整理结果
        final_results = self._organize_results(results, batch_items)
        
        # 生成摘要
        self._generate_summary(final_results, time.time() - start_time)
        
        return final_results

    def _organize_results(self, results: List, batch_items: List) -> List[Tuple[str, bool, str]]:
        """整理结果确保顺序正确"""
        sorted_results = [None] * len(batch_items)
        for i, result in results:
            if i < len(batch_items):
                sorted_results[i] = result
        
        # 填充缺失结果
        return [
            sorted_results[i] if sorted_results[i] is not None 
            else (batch_items[i]["url"], False, "任务未完成")
            for i in range(len(batch_items))
        ]

    def _generate_summary(self, results: List[Tuple[str, bool, str]], total_elapsed: float):
        """生成执行摘要"""
        total = len(results)
        success_count = sum(1 for _, success, _ in results if success)
        
        self.logger.info("=" * 50)
        self.logger.info("执行摘要:")
        self.logger.info(f"  总任务数: {total}")
        self.logger.info(f"  成功数量: {success_count}")
        self.logger.info(f"  成功率: {(success_count/total)*100:.1f}%")
        self.logger.info(f"  总耗时: {total_elapsed:.1f}秒")
        self.logger.info("=" * 50)
        
        # 输出找到的Flag
        found_flags = [flag for _, success, flag in results if success and flag]
        if found_flags:
            print("\n发现的Flag:")
            for flag in found_flags:
                print(f"  {flag}")

    def close(self):
        """安全关闭"""
        self.logger.info("关闭进程池...")
        try:
            self.process_pool.close()
            self.process_pool.join(timeout=0.1)
        except:
            self.process_pool.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 模块级函数 - 这些可以在子进程中安全执行
def execute_single_task(task_data: Dict[str, Any]) -> Tuple[str, bool, str]:
    """在独立进程中执行单个任务 - 模块级函数避免序列化问题"""
    # 在子进程中设置日志
    logger = setup_task_logger(task_data['code'])
    
    url = task_data['url']
    challenge_code = task_data['code']
    
    try:
        logger.info(f"开始执行任务: {challenge_code} - {url}")
        start_time = time.perf_counter()
        # 获取提示信息
        hint_text = get_hint_if_needed(challenge_code, task_data['hint_last_hour'], logger)
        # 为每题设置独立的命名空间，避免记忆混淆
        # target_key = f"ctf_{task_data['code']}_{task_data['url'].replace('://', '_').replace('/', '_')}"
        # os.environ["CREWAI_STORAGE_DIR"] = f"{target_key}"
        
        # 执行CTF逻辑 - 在子进程中创建执行器
        executor = CTFExecutor(cdp_url=task_data['cdp_url'])
        result = executor.execute_ctf(
            str(challenge_code), 
            url, 
            hint_text, 
            task_data.get('failure_counts', 0)
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        elapsed_str = format_duration(elapsed_ms)
        logger.info(f"任务完成: {challenge_code} - 耗时: {elapsed_str}")
        
        # 验证结果
        flag_found, flag_content = validate_result(result, challenge_code, logger)
        
        if flag_found:
            auto_submit_flag(challenge_code, flag_content, logger)
            logger.info(f"任务成功 - 找到Flag: {flag_content}")
        else:
            logger.info("任务完成但未找到Flag")
        
        return (url, flag_found, flag_content)
        
    except Exception as e:
        logger.error(f"任务执行失败: {e} {traceback.format_exc()}")
        return (url, False, f"执行异常: {str(e)}")

def setup_task_logger(challenge_code: str):
    """设置任务专用日志器 - 模块级函数"""
    safe_code = "".join(c for c in str(challenge_code) if c.isalnum() or c in ('-', '_'))
    logger = get_logger(f"task.{safe_code}")
    return logger


def get_hint_if_needed(challenge_code: str, hint_last_hour: bool, logger) -> str:
    """获取提示信息 - 模块级函数"""
    if not (hint_last_hour and challenge_code):
        return None
        
    try:
        if is_in_last_hour_of_competition() or is_debug():
            raw_hint = get_ctf_hint(str(challenge_code)) if get_ctf_hint else ""
            hint_obj = json.loads(raw_hint or "{}") if isinstance(raw_hint, str) else raw_hint
            return hint_obj.get("hint_content")
    except Exception as e:
        logger.error(f"获取提示失败: {e}")
        
    return None


def validate_result(result: str, challenge_code: str, logger) -> Tuple[bool, str]:
    """验证执行结果 - 模块级函数"""
    try:
        from lib.tools import FlagValidatorTool
        fv = FlagValidatorTool()
        validation = fv._run(str(result))
        
        flag_found = validation.startswith("✅ 发现有效Flag")
        flag_content = validation.split(":", 1)[1].strip() if flag_found else ""
        
        return flag_found, flag_content
    except Exception as e:
        logger.error(f"验证结果失败: {e}")
        return False, ""


def auto_submit_flag(challenge_code: str, flag_content: str, logger):
    """自动提交Flag - 模块级函数"""
    try:
        if submit_ctf_flag:
            submit_res = submit_ctf_flag(str(challenge_code), flag_content)
            logger.info(f"Flag提交成功:{challenge_code} - {submit_res}")
    except Exception as e:
        logger.error(f"Flag提交失败:{challenge_code} - {e}")


# 全局执行器实例
_executor = None

def run_batch_for_items(batch_items: List[Dict[str, Any]], args) -> List[Tuple[str, bool, str]]:
    """主要执行函数"""
    global _executor
    
    cdp_urls = get_cdp_urls()
    
    logger = get_logger("main")
    
    if _executor is None:
        _executor = PebbleCTFExecutor(cdp_urls, max_concurrent=args.max_concurrent)
    
    try:
        return _executor.run_batch_concurrently(batch_items, args)
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return [(item["url"], False, f"执行异常: {e}") for item in batch_items]


def get_cdp_urls() -> List[str]:
    """获取CDP URLs"""
    cdp_urls_str = os.getenv("CDP_URLS", "")
    if cdp_urls_str:
        return [url.strip() for url in cdp_urls_str.split(",") if url.strip()]
    return [os.getenv("STEEL_CONNECT_URL", "ws://127.0.0.1:13001")]


# 清理函数
import atexit
def cleanup():
    if _executor:
        _executor.close()
atexit.register(cleanup)

import signal
def signal_handler(sig, frame):
    cleanup()
    exit(0)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
