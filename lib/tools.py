from datetime import datetime
import logging
import re
import shlex
import subprocess
import os
import asyncio
# import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Type, Optional, Any
from contextlib import asynccontextmanager
import requests_raw
import json
import time

from pydantic import BaseModel, Field, PrivateAttr
from crewai.tools import BaseTool
from browser_use import Agent as BrowserAgent, BrowserSession, Tools
from steel import Client

from lib.llm import BrowserLLM

# 配置
browser_use_tools = Tools(exclude_actions=["search"])

# 日志配置
logger = logging.getLogger("main")

class BrowserSessionConfig:
    """浏览器会话配置"""
    def __init__(self):
        self.cdp_url = os.getenv("STEEL_CONNECT_URL", "ws://127.0.0.1:13001")
        self.headless = True
        self.keep_alive = True
        self.record_har_path = f"/app/browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.har"
        self.disable_security = True

class ToolExecutionError(Exception):
    """工具执行异常"""
    pass

class BrowserSessionManager:
    """浏览器会话管理器"""
    
    def __init__(self, config: BrowserSessionConfig):
        self.config = config
        self.browser: Optional[BrowserSession] = None
        self.steel_client = Client(
            base_url=self.config.cdp_url.replace("ws://", "http://"), 
            steel_api_key="keys"
        )
        self.session = None
        self._is_active = False

    async def start(self) -> BrowserSession:
        """启动浏览器会话"""
        if self._is_active:
            return self.browser
            
        try:
            self.session = self.steel_client.sessions.create()
            
            self.browser = BrowserSession(
                is_local=True,
                headless=self.config.headless,
                cdp_url=self.config.cdp_url,
                keep_alive=self.config.keep_alive,
                record_har_path=self.config.record_har_path,
                disable_security=self.config.disable_security,
            )
            
            await self.browser.start()
            self._is_active = True
            logger.info("✅ 浏览器会话启动成功")
            return self.browser
            
        except Exception as e:
            logger.error(f"❌ 浏览器会话启动失败: {e}")
            raise ToolExecutionError(f"浏览器启动失败: {e}")

    async def stop(self):
        """停止浏览器会话"""
        if not self._is_active:
            return
            
        try:
            if self.browser:
                await self.browser.kill()
            if self.session:
                self.steel_client.sessions.release(self.session.id)
                
            self._is_active = False
            logger.info("✅ 浏览器会话已关闭")
            
        except Exception as e:
            logger.error(f"❌ 浏览器会话关闭失败: {e}")
            # 不重新抛出异常，确保资源释放


class BrowserAgentManager:
    """BrowserAgent管理器 - 单实例"""
    
    def __init__(self, session_manager: BrowserSessionManager):
        self.session_manager = session_manager
        self.agent: Optional[BrowserAgent] = None
        self.task_history: List[Dict] = []
        self.is_initialized = False

    @asynccontextmanager
    async def browser_context(self):
        """浏览器上下文管理器"""
        try:
            await self.initialize()
            yield self
        finally:
            await self.close()

    async def initialize(self):
        """初始化BrowserAgent"""
        if self.is_initialized:
            return
            
        logger.info("[BrowserAgentManager] 初始化浏览器代理")
        
        try:
            browser = await self.session_manager.start()
            
            # 创建BrowserAgent
            self.agent = BrowserAgent(
                task="作为一个CTF-WEB安全专家助手，你的任务是根据用户的问题和上下文，使用浏览器工具进行快速的安全发现和快速测验。\n"
                "注意严格按照我指出的URL进行访问操作，不要访问到别的IP端口了。\n"
                "【内嵌工具】evaluate - Execute custom JavaScript code on the page (for advanced interactions, shadow DOM, custom selectors, data extraction)，requires arrow function format: () => {}(),(() => {javascript code})()\n"
                "如果需要的话，可以通过evaluate工具执行js获取cookie等信息，没有获取到就说没有就行。不要重复执行相同的js代码。\n",
                browser_session=browser,
                llm=BrowserLLM,
                tools=browser_use_tools,
                use_vision=False,
                use_thinking=False,
                step_timeout=60,
                max_failures=2,
                # max_retries=2,
                llm_timeout=60,
                flash_mode=True
            )
            
            self.is_initialized = True
            logger.info("✅ BrowserAgent初始化完成")
            
        except Exception as e:
            logger.error(f"❌ BrowserAgent初始化失败: {e}")
            raise ToolExecutionError(f"BrowserAgent初始化失败: {e}")

    async def execute_task(self, task_description: str, max_steps: int = 10) -> Dict[str, Any]:
        """执行单个浏览器任务"""
        if not self.is_initialized:
            await self.initialize()
        
        logger.info(f"[BrowserAgentManager] 开始任务: {task_description} | 步数上限: {max_steps}")
        
        try:
            # 添加新任务
            self.agent.add_new_task(task_description)
            
            # 执行任务
            history = await self.agent.run(max_steps=max_steps)
            
            # 记录任务结果
            task_result = {
                'task': task_description,
                'result': history.final_result(),
                'visited_urls': history.urls(),
                'actions': history.action_names(),
                'screenshots': len(history.screenshots()),
                'steps': history.number_of_steps(),
                'success': True
            }
            
            self.task_history.append(task_result)
            logger.info(f"[BrowserAgentManager] 任务完成: {task_description} | 步数: {task_result['steps']}")
            
            return task_result
            
        except Exception as e:
            error_result = {
                'task': task_description,
                'error': str(e),
                'result': None,
                'success': False
            }
            self.task_history.append(error_result)
            logger.error(f"[BrowserAgentManager] 任务失败: {task_description} | 错误: {e}")
            return error_result

    async def execute_tasks_sequence(self, tasks: List[str], max_steps_per_task: int = 10) -> List[Dict]:
        """顺序执行多个任务"""
        results = []
        
        async with self.browser_context():
            for i, task in enumerate(tasks, 1):
                logger.info(f"🔄 执行任务 {i}/{len(tasks)}: {task[:50]}...")
                
                result = await self.execute_task(task, max_steps_per_task)
                results.append(result)
                
                # 短暂暂停避免过快请求
                await asyncio.sleep(1)
        
        return results

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        successful_tasks = [t for t in self.task_history if t.get('success')]
        failed_tasks = [t for t in self.task_history if not t.get('success')]
        
        return {
            'total_tasks': len(self.task_history),
            'successful_tasks': len(successful_tasks),
            'failed_tasks': len(failed_tasks),
            'total_visited_urls': sum(len(t.get('visited_urls', [])) for t in successful_tasks),
            'total_actions': sum(len(t.get('actions', [])) for t in successful_tasks)
        }

    async def close(self):
        """关闭浏览器管理器"""
        if self.is_initialized:
            await self.session_manager.stop()
            self.is_initialized = False
            logger.info("✅ BrowserAgentManager已关闭")


class CommandExecutor:
    """命令执行器 - 统一处理子进程执行"""
    
    @staticmethod
    def execute_command(
        command: List[str],
        operation: str,
        timeout: int = 300,
        shell: bool = False,
        cwd: Optional[str] = None
    ) -> str:
        """执行命令并返回结果"""
        try:
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                
                if process.returncode == 0:
                    return CommandExecutor._format_success_output(stdout, operation)
                else:
                    return CommandExecutor._format_error_output(
                        operation, 
                        f"退出码: {process.returncode}", 
                        stderr, 
                        stdout
                    )
                    
            except subprocess.TimeoutExpired:
                # 超时时强制终止进程并获取已有输出
                process.kill()
                stdout, stderr = process.communicate()  # 获取已有的输出
                
                return CommandExecutor._format_error_output(
                    operation, 
                    "命令执行超时，输出如下", 
                    stderr, 
                    stdout
                )
                
        except Exception as e:
            return CommandExecutor._format_error_output(operation, f"执行错误: {str(e)}")

    @staticmethod
    def _format_success_output(output: str, operation: str) -> str:
        """格式化成功输出"""
        preview = output[:4000] + "..." if len(output) > 4000 else output
        return f"✅ {operation} - 执行成功\n{preview}"

    @staticmethod
    def _format_error_output(operation: str, error: str, stderr: str = "", stdout: str = "") -> str:
        """格式化错误输出"""
        error_msg = f"❌ {operation} - {error}"
        
        if stderr:
            stderr_preview = stderr[:2000] + "..." if len(stderr) > 2000 else stderr
            error_msg += f"\nSTDERR:\n{stderr_preview}"
            
        if stdout:
            stdout_preview = stdout[:1000] + "..." if len(stdout) > 1000 else stdout
            error_msg += f"\nSTDOUT:\n{stdout_preview}"
            
        return error_msg

class SQLMapToolInput(BaseModel):
    """SQLMap工具输入参数"""
    target_url: str = Field(None, description="目标URL")
    action: str = Field("detect", description="动作类型：detect/dbs/tables/dump/execute")
    extra_params: Optional[str] = Field("--batch --level=2 --random-agent --time-sec=5", description="额外的sqlmap命令参数串，会追加到命令末尾")
    command: Optional[str] = Field(None, description="当action=execute时的完整sqlmap命令参数串")
    database: Optional[str] = Field(None, description="当action=tables/dump时的数据库名")
    table: Optional[str] = Field(None, description="当action=dump时的表名")
    limit: int = Field(50, description="dump限制条数")

class SQLMapTool(BaseTool):
    """自动化SQL注入检测和利用工具"""
    
    name: str = "SQLMapTool"
    description: str = (
        "自动化SQL注入检测和利用工具。注意：如果是POST请求，需要在extra_params中添加--data参数。默认参数：--batch --level=2 --random-agent --time-sec=5 "
        "支持的操作："
        "- detect: 检测SQL注入"
        "- dbs: 枚举数据库"
        "- tables: 枚举指定数据库的表（需要database参数）"
        "- dump: 提取表数据（需要database和table参数）"
        "- execute: 执行自定义sqlmap命令（需要command参数）"
    )
    args_schema: Type[BaseModel] = SQLMapToolInput

    def _run(self, target_url: Optional[str] = None, action: str = "detect", extra_params: Optional[str] = "--batch --level=2 --random-agent --time-sec=5", **kwargs) -> str:
        """执行SQLMap扫描"""
        if not target_url and "-u" not in kwargs.get("command", ""):
            return "❌ 目标URL不能为空"
        
        if "--batch" not in extra_params:
            extra_params += " --batch"
            
        actions = {
            "detect": self._detect_injection,
            "dbs": self._get_databases,
            "tables": self._get_tables,
            "dump": self._dump_data,
            "execute": self._execute_custom_command
        }
        
        func = actions.get(action)
        if not func:
            return f"❌ 不支持的操作类型: {action}，支持的操作: {', '.join(actions.keys())}"
            
        try:
            # 明确传递参数，避免重复
            if action == "execute":
                command = kwargs.get("command")
                return self._execute_custom_command(target_url, command, extra_params)
            elif action == "tables":
                database = kwargs.get("database")
                return self._get_tables(target_url, database, extra_params)
            elif action == "dump":
                database = kwargs.get("database")
                table = kwargs.get("table")
                limit = kwargs.get("limit", 50)
                return self._dump_data(target_url, database, table, limit, extra_params)
            else:
                # detect 和 dbs 只需要基础参数
                return func(target_url, extra_params)
        except Exception as e:
            return f"❌ SQLMap执行失败: {str(e)}"

    def _detect_injection(self, target_url: str, extra_params: Optional[str] = None, **kwargs) -> str:
        """检测SQL注入"""
        base_cmd = f"-u \"{target_url}\""
        cmd = self._build_command(base_cmd, extra_params)
        return self._execute_sqlmap_command(cmd, "SQL注入检测")

    def _get_databases(self, target_url: str, extra_params: Optional[str] = None, **kwargs) -> str:
        """枚举数据库"""
        base_cmd = f"-u \"{target_url}\" --dbs"
        cmd = self._build_command(base_cmd, extra_params)
        return self._execute_sqlmap_command(cmd, "数据库枚举")

    def _get_tables(self, target_url: str, database: str, extra_params: Optional[str] = None, **kwargs) -> str:
        """枚举表"""
        if not database:
            return "❌ 枚举表需要指定database参数"
            
        base_cmd = f"-u \"{target_url}\" -D {self._sanitize_param(database)} --tables"
        cmd = self._build_command(base_cmd, extra_params)
        return self._execute_sqlmap_command(cmd, f"表枚举 - {database}")

    def _dump_data(self, target_url: str, database: str, table: str, limit: int = 50, extra_params: Optional[str] = None, **kwargs) -> str:
        """提取数据"""
        if not database or not table:
            return "❌ 数据提取需要指定database和table参数"
            
        base_cmd = f"-u \"{target_url}\" -D {self._sanitize_param(database)} -T {self._sanitize_param(table)} --dump --start=1 --stop={limit}"
        cmd = self._build_command(base_cmd, extra_params)
        return self._execute_sqlmap_command(cmd, f"数据提取 - {database}.{table} (前{limit}条)")

    def _execute_custom_command(self, target_url: str, command: str, extra_params: Optional[str] = None, **kwargs) -> str:
        """执行自定义命令"""
        if not command:
            return "❌ 执行命令失败 - 未提供command参数"
            
        # 对于自定义命令，不自动添加默认参数
        cmd = self._build_command(f"-u \"{target_url}\" " + command, extra_params, include_defaults=False)
        return self._execute_sqlmap_command(cmd, "执行自定义命令")

    def _build_command(self, base_cmd: str, extra_params: Optional[str] = None, include_defaults: bool = True) -> str:
        """构建完整的命令"""
        cmd = base_cmd
        if extra_params:
            cmd += f" {extra_params.strip()}"
        if "--disable-coloring" not in cmd:
            cmd += " --disable-coloring"
        return cmd

    def _sanitize_param(self, param: str) -> str:
        """参数清理，防止命令注入"""
        # 移除可能危险的字符
        sanitized = re.sub(r'[;&|$`]', '', param)
        return shlex.quote(sanitized)

    def _execute_sqlmap_command(self, command: str, operation: str) -> str:
        """执行SQLMap命令"""
        try:
            container = os.getenv("SQLMAP_CONTAINER", "sqlmap")
            entrypoint = os.getenv("SQLMAP_ENTRYPOINT", "sqlmap-dev/sqlmap.py")
            
            # 使用更安全的命令构建方式
            docker_base = os.getenv("DOCKER_BIN", "docker").split(" ")
            
            # 安全地分割命令
            sqlmap_args = shlex.split(command)
            
            # 构建完整的Docker命令
            docker_cmd = docker_base + ["exec", "-t", container, entrypoint] + sqlmap_args
            # print(docker_cmd)
            
            result = CommandExecutor.execute_command(docker_cmd, operation, timeout=120)
            
            # 增强的结果解析
            if any(msg in result.lower() for msg in [
                "all tested parameters do not appear to be injectable",
                "no injection detected"
            ]):
                return f"✅ {operation} - 未发现SQL注入漏洞\n\n详细输出:\n{result}"
                
            elif any(msg in result.lower() for msg in [
                "sqlmap identified the following injection point",
                "injection point"
            ]):
                return f"🎯 {operation} - 发现SQL注入漏洞!\n\n详细输出:\n{result}"
                
            elif "error" in result.lower() or "exception" in result.lower():
                return f"⚠️ {operation} - 执行过程中出现错误\n\n错误信息:\n{result}"
                
            else:
                return f"📊 {operation} - 执行完成\n\n输出结果:\n{result}"
                
        except Exception as e:
            return f"❌ {operation} - 命令执行失败: {str(e)}"


class BrowserTool(BaseTool):
    """浏览器控制工具"""
    
    name: str = "BrowserTool"
    description: str = "控制浏览器进行网页导航和交互"
    
    # 使用 PrivateAttr 来存储非Pydantic字段
    _session_manager: BrowserSessionManager = PrivateAttr()
    _agent_manager: Optional[BrowserAgentManager] = PrivateAttr()

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None, **kwargs):
        super().__init__(**kwargs)
        # 使用 PrivateAttr 来设置非Pydantic字段
        self._session_manager = session_manager or BrowserSessionManager(BrowserSessionConfig())
        self._agent_manager = None

    async def _arun(self, task_description: str, **kwargs) -> str:
        """异步执行浏览器任务"""
        try:
            if self._agent_manager is None:
                self._agent_manager = BrowserAgentManager(self._session_manager)
            
            max_steps = kwargs.get("max_steps", 10)
            
            async with self._agent_manager.browser_context():
                result = await self._agent_manager.execute_task(task_description, max_steps=max_steps)
                
            return self._format_browser_result(task_description, result)
            
        except Exception as e:
            logger.error(f"浏览器任务执行失败: {e}")
            return f"❌ 浏览器任务执行失败: {e}"

    def _format_browser_result(self, task: str, result: Dict) -> str:
        """格式化浏览器任务结果"""
        if result.get('success'):
            return (
                f"✅ 浏览器任务完成: {task}\n"
                f"结果: {result.get('result', 'N/A')}\n"
                f"访问URL: {', '.join(set(result.get('visited_urls', [])))}\n"
                f"执行步骤: {result.get('steps', 0)}步"
            )
        else:
            return f"❌ 浏览器任务失败: {task}\n错误: {result.get('error', 'Unknown error')}"

    def _run(self, task_description: str, **kwargs) -> str:
        """同步执行浏览器任务"""
        def run_async_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._arun(task_description, **kwargs))
            finally:
                loop.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_task)
            return future.result()


class CTFDirSearchTool(BaseTool):
    """目录搜索工具"""
    
    name: str = "DirectorySearcher"
    description: str = "在目标网站上搜索可能的目录和信息泄露, 注意只对target_url以/结尾的目录进行探测"

    def _run(self, target_url: str) -> str:
        """执行目录搜索"""
        try:
            command = ["python", "ctf-wscan.py", target_url]
            return CommandExecutor.execute_command(
                command, 
                "目录搜索", 
                timeout=60, 
                cwd="ctf-wscan"
            )
        except Exception as e:
            return f"❌ 目录搜索失败: {e}"


class FlagValidatorTool(BaseTool):
    """Flag验证工具"""
    
    name: str = "FlagValidator"
    description: str = "验证flag格式和有效性"

    def _run(self, content: str) -> str:
        """验证Flag格式"""
        if not content:
            return "❌ 输入内容为空"
            
        patterns = [
            r"flag\{[^}]+\}",
            r"CTF\{[^}]+\}", 
            r"FLAG\{[^}]+\}",
            # r"[A-Za-z0-9]{32}",  # 32位MD5类Flag
            # r"[A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{12}",  # UUID格式
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return f"✅ 发现有效Flag格式: {', '.join(matches[:3])}"  # 限制显示数量
                
        return "❌ 未发现有效Flag格式"


class SandboxExecTool(BaseTool):
    """沙箱执行工具"""
    
    name: str = "SandboxExec"
    description: str = "在沙箱内执行命令（包含curl、python、php、base64等linux命令）"

    def _run(self, command: str, timeout: int = 120) -> str:
        """在沙箱中执行命令"""
        container = os.getenv("SANDBOX_CONTAINER", os.getenv("SQLMAP_CONTAINER", "sqlmap"))
        
        # 检测是否需要shell
        needs_shell = any(sym in command for sym in ["|", "&&", ";", "||", "`", "$(", ">", "<", "\n"])
        
        if not needs_shell:
            # 直接执行命令
            docker_cmd = [
                *os.getenv("DOCKER_BIN", "docker").split(" "),
                "exec", "-t", container
            ] + shlex.split(command)
        else:
            # 通过shell执行
            shell_prog = os.getenv("SANDBOX_SHELL", "sh")
            docker_cmd = [
                *os.getenv("DOCKER_BIN", "docker").split(" "),
                "exec", "-t", container,
                shell_prog, "-lc", command
            ]
        
        return CommandExecutor.execute_command(docker_cmd, "沙箱执行", timeout=timeout)


class KatanaTool(BaseTool):
    """Katana网页爬虫工具"""
    
    name: str = "KatanaTool"
    description: str = "在docker katana容器中运行katana，提取页面的XHR端点等http请求包并以JSONL输出"

    def _run(self, target_url: str) -> str:
        """执行Katana爬虫"""
        container = os.getenv("KATANA_CONTAINER", "katana")
        
        katana_cmd = [
            *os.getenv("DOCKER_BIN", "docker").split(" "),
            "exec", "-t", container,
            "katana",
            "-u", target_url,
            "-d", "2",
            "-fdc", "status_code==404",
            "-ef", "png,jpg,jpeg,gif,css",
            "-ct", "1m",
            "-sr",
            # "-sc", "-nos", "-hl",
            "-timeout", "8",
            # "-kf", "all",
            "-silent",  "-duc", "-fx", "-jc", "-xhr", "-jsonl", "-aff",
             "-fs", "dn", "-aff"
        ]
        
        return CommandExecutor.execute_command(katana_cmd, "Katana爬虫", timeout=61)

class RawHttpToolInput(BaseModel):
    """原始HTTP请求工具输入参数"""
    url: str = Field(..., description="目标URL")
    raw_request: str = Field(..., description="原始HTTP请求报文(注意HTTP报文格式,尤其是空格、换行、URL编码)")
    timeout: Optional[float] = Field(15.0, description="请求超时时间(秒)")
    start_response_index: Optional[int] = Field(0, description="截取响应内容起始索引(字节)")
    end_response_index: Optional[int] = Field(8000, description="截取响应内容结束索引(字节)")
    redirect: Optional[bool] = Field(False, description="是否允许重定向, False可观察响应头，比如cookie")

class RawHttpTool(BaseTool):
    """原始HTTP请求工具 - 用于SQL注入、SSTI、文件上传等安全测试"""
    
    name: str = "RawHttpTool"
    description: str = "发送原始HTTP请求，支持自定义请求报文（注意HTTP报文格式，尤其是空格、换行、URL编码），适合各种安全测试场景"
    args_schema: Type[BaseModel] = RawHttpToolInput

    def _run(
        self, 
        url: str,
        raw_request: str,
        timeout: float = 15.0,
        start_response_index: int = 0,
        end_response_index: int = 8000,
        redirect: bool = False,
        **kwargs
    ) -> str:
        """
        发送原始HTTP请求
        
        Args:
            url: 目标URL
            raw_request: 原始HTTP请求报文(注意HTTP报文格式,尤其是空格、换行、URL编码)
            timeout: 超时时间(秒)
        """
        try:
            auto_fix_content_length = True
            # 解析并预处理原始请求
            request_uri, processed_request = self._parse_and_fix_raw_request(raw_request, auto_fix_content_length)
            
            # 确保是字节类型
            if isinstance(processed_request, str):
                processed_request = processed_request.encode('utf-8')
            
            # if max_response_length > 10240:
            #     max_response_length = 10240
            
            # 发送原始HTTP请求
            start_time = time.time()
            response = requests_raw.raw(
                url=url, 
                data=processed_request,
                timeout=timeout,
                verify=False,
                allow_redirects=redirect
            )
            response_time = round(time.time() - start_time, 2)
            
            # 处理响应内容长度
            response_text = response.text
            text_end = min(end_response_index, len(response_text))
            response_text = response_text[start_response_index:text_end]
            
            # 构建响应结果
            result = [
                "✅ 请求成功",
                f"目标URL: {url}",
                f"请求URI: {request_uri}",
                f"状态码: {response.status_code}",
                f"响应时间: {response_time}s",
                f"内容长度: {len(response.content or '')} bytes",
                f"返回响应区间: [{start_response_index}, {end_response_index}] 字符",
                f"响应内容原始长度: {len(response.text)} 字符",
                f"未显示响应内容长度: {len(response_text) - text_end + start_response_index} 字符",
                "",
                "📨 响应头部:",
            ]
            
            # 添加响应头
            for key, value in list(response.headers.items())[:15]:
                result.append(f"  {key}: {value}")
            
            # 响应内容
            result.append("")
            result.append("📄 响应内容:")
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                try:
                    json_response = response.json()
                    # JSON也受长度限制
                    json_str = json.dumps(json_response, indent=2, ensure_ascii=False)
                    # if len(json_str) > end_response_index - start_response_index:
                    #     json_str = json_str[:end_response_index - start_response_index]
                    result.append(json_str)
                except:
                    result.append(response_text)
            else:
                result.append(response_text)
            
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ 请求失败: {e}"

    def _parse_and_fix_raw_request(self, raw_request: str, auto_fix_content_length: bool = True) -> str:
        """
        解析原始HTTP请求并自动修复Content-Length
        
        Args:
            raw_request: 原始HTTP请求字符串
            auto_fix_content_length: 是否自动修复Content-Length
            
        Returns:
            修复后的HTTP请求字符串
        """
        sep = "\n"
        first_line = raw_request.split(sep)[0]
        if first_line.endswith("\r"):
            sep = "\r\n"

        if raw_request.startswith("GET") and sep + sep not in raw_request:
            if raw_request.endswith(sep):
                raw_request += sep
            else:
                raw_request += sep + sep


        # 将请求按空行分割为头部和主体
        pa1 = raw_request.split(sep, 1)
        if len(pa1) == 2:
            pa2 = pa1[0].split(" ", 1)
            if len(pa2) == 2 and pa2[1].count(" ") > 1:
                raw_request = pa2[0] + " " + pa2[1].replace(" ", "+").replace("+HTTP/", " HTTP/") + sep + pa1[1]
            
        parts = raw_request.split(sep + sep, 1)
        if len(parts) == 1:
            # 如果没有明确的主体部分，直接返回原请求
            # 尝试从单行请求中解析URL
            try:
                first_line = raw_request.split(sep)[0]
                parts_line = first_line.split(" ")
                if len(parts_line) >= 2:
                    return parts_line[1], raw_request
            except Exception:
                pass
            return raw_request
            
        headers_part, body_part = parts
        
        # 解析头部
        headers_lines = headers_part.split(sep)
        if not headers_lines:
            return raw_request
            
        request_line = headers_lines[0]  # 第一行是请求行
        header_lines = headers_lines[1:]  # 其余是头部

        request_line_split = request_line.split(" ")
        if len(request_line_split) >= 2:
            url = request_line_split[1]
        else:
            url = ""
        # method = request_line_split[0]
        # http_version = request_line_split[2] if len(request_line_split) > 2 else ""
        
        # 处理主体
        body = body_part.strip()
        body_length = len(body.encode('utf-8'))  # 计算字节长度
        
        # 重建头部，处理Content-Length
        new_headers = [request_line]
        content_length_found = False
        
        for line in header_lines:
            if line.strip():  # 跳过空行
                if line.lower().startswith('content-length:'):
                    if auto_fix_content_length:
                        # 替换为正确的Content-Length
                        new_headers.append(f"Content-Length: {body_length}")
                        content_length_found = True
                    else:
                        # 保持原样
                        new_headers.append(line)
                        content_length_found = True
                else:
                    new_headers.append(line)
        
        # 如果没有找到Content-Length头部且需要自动修复，则添加
        if auto_fix_content_length and not content_length_found and body:
            new_headers.append(f"Content-Length: {body_length}")
        
        # 重新构建请求
        fixed_request = sep.join(new_headers) + sep + sep + body
        
        return url, fixed_request

    def _calculate_content_length(self, body: str) -> int:
        """
        计算HTTP主体的字节长度
        
        Args:
            body: HTTP主体内容
            
        Returns:
            字节长度
        """
        return len(body.encode('utf-8'))



def setup_tools(cdp_url: str = None) -> Dict[str, BaseTool]:
    """初始化并返回所有工具"""
    
    # 创建共享的浏览器会话管理器
    session_manager = None
    if cdp_url is not None:
        browser_config = BrowserSessionConfig()
        browser_config.cdp_url = cdp_url
        session_manager = BrowserSessionManager(browser_config)
    
    return {
        "dir_searcher": CTFDirSearchTool(),
        "katana": KatanaTool(),
        "browser": BrowserTool(session_manager=session_manager), 
        "sqlmap": SQLMapTool(),
        "sandbox_exec": SandboxExecTool(),
        "flag_validator": FlagValidatorTool(),
        "raw_http": RawHttpTool()
    }


# 全局工具实例缓存
_tool_instances: Optional[Dict[str, BaseTool]] = None

def get_tools() -> Dict[str, BaseTool]:
    """获取工具实例（单例模式）"""
    global _tool_instances
    if _tool_instances is None:
        _tool_instances = setup_tools()
    return _tool_instances



if __name__ == "__main__":
    tools = get_tools()
    print(tools.keys())


    # test sqlmap tool
    sqlmap_tool = tools["sqlmap"]
    print(sqlmap_tool._run("http://222.20.126.53:32809", action="detect", extra_params="--batch --level=3 --risk=2"))