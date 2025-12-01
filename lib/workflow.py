from crewai import Task, Agent
from crewai.knowledge.knowledge_config import KnowledgeConfig

# from .agents import ComprehensiveCTFAgents, RobustCTFAgents, ReasoningCTFAgents
# from .tools import CTFDirSearchTool, KatanaTool, BrowserTool, SQLMapTool, SandboxExecTool, FlagValidatorTool
# class CTFCrewAISystem:
#     """全面的CTF系统"""
    
#     def __init__(self, llm_config):
#         self.llm_config = llm_config
#         self.tools = self._setup_tools()
#         self.agent_builder = ComprehensiveCTFAgents(self.llm_config, self.tools)
#         self.agents = self.agent_builder.get_all_agents()
#         self.robust_agent_builder = RobustCTFAgents(self.llm_config, self.tools)
#         self.robust_agents = self.robust_agent_builder.get_all_agents()
    
#     def _setup_tools(self):
#         """工具设置"""
#         return {
#             "dir_searcher": CTFDirSearchTool(),
#             "katana": KatanaTool(),
#             "browser": BrowserTool(), 
#             "sqlmap": SQLMapTool(),
#             "sandbox_exec": SandboxExecTool(),
#             "flag_validator": FlagValidatorTool()
#         }
    
#     def create_comprehensive_workflow(self, target_url: str, target_code: str, hint: str | None = None):
#         """创建全面的工作流程"""
        
#         # 第一阶段：全面侦察
#         recon_task = Task(
#             description=f"全面侦察目标: (url:{target_url}，题目编号: {target_code})，提示：({hint})",
#             agent=self.agents["reconnaissance_master"],
#             expected_output="完整的技术栈信息和攻击面地图"
#         )
        
#         # 第二阶段：并行漏洞测试（主要漏洞类型）
#         injection_task = Task(
#             description=f"全面注入漏洞测试，提示：({hint})",
#             agent=self.agents["injection_specialist"],
#             context=[recon_task],
#             expected_output="注入漏洞测试结果和利用方法",
#             async_execution=True
#         )
        
#         access_task = Task(
#             description=f"访问控制漏洞测试，提示：({hint})", 
#             agent=self.agents["access_control_expert"],
#             context=[recon_task],
#             expected_output="访问控制漏洞测试结果和利用方法",
#             async_execution=True
#         )
        
#         # 客户端漏洞Agent暂未定义，注释以避免运行时 KeyError
#         # 如需恢复，请在 agents.py 定义 _create_client_side_hunter 并于 get_all_agents 启用
#         # client_task = Task(
#         #     description=f"客户端漏洞测试，提示：({hint})",
#         #     agent=self.agents["client_side_hunter"], 
#         #     context=[recon_task],
#         #     async_execution=True
#         # )
        
#         file_task = Task(
#             description=f"文件系统漏洞测试，提示：({hint})",
#             agent=self.agents["file_system_explorer"],
#             context=[recon_task],
#             expected_output="文件系统漏洞测试结果和利用方法",
#             async_execution=True 
#         )
        
#         server_task = Task(
#             description=f"服务器端漏洞测试，提示：({hint})",
#             agent=self.agents["server_side_attacker"],
#             context=[recon_task],
#             expected_output="服务器端漏洞测试结果和利用方法",
#             async_execution=True
#         )
        
#         protocol_task = Task(
#             description=f"协议级漏洞测试，提示：({hint})",
#             agent=self.agents["protocol_abuser"],
#             context=[recon_task],
#             expected_output="协议级漏洞测试结果和利用方法",
#             async_execution=True
#         )
        
#         # 第三阶段：协调和报告
#         coordination_task = Task(
#             description=f"协调所有测试并生成最终报告，提示：({hint})",
#             agent=self.agents["vulnerability_orchestrator"],
#             context=[recon_task, injection_task, access_task, file_task, server_task, protocol_task],
#             expected_output="完整的攻击报告和flag验证"
#         )
        
#         return [
#             recon_task,
#             injection_task,
#             access_task,
#             # client_task, 
#             file_task,
#             server_task,
#             protocol_task,
#             coordination_task
#         ]

#     def create_safe_workflow(self, target_url: str, target_code: str, hint: str | None = None):
#         """创建安全的工作流"""
        
#         # 第一阶段：受限侦察
#         scout_task = Task(
#             description=(
#                 f"智能侦察目标: (url:{target_url}，题目编号: {target_code})。提示：({hint})\n"
#                 "限制：最大10分钟，最多50个请求，避免重复扫描\n"
#                 "重点：管理员功能、文件上传、API端点、常见漏洞文件"
#             ),
#             agent=self.robust_agents["intelligent_scout"],
#             expected_output="关键攻击目标清单和漏洞提示",
#             async_execution=False
#         )
        
#         # 第二阶段：定向漏洞检测
#         detection_task = Task(
#             description=(
#                 f"基于侦察结果进行针对性漏洞验证，提示：({hint})\n"
#                 "限制：每个端点最大3分钟，必须有实际证据\n"
#                 "【防幻觉】不假设漏洞存在，基于工具实际响应判断\n"
#                 "重点：SQL注入、命令注入、文件包含、权限绕过"
#             ),
#             agent=self.robust_agents["vulnerability_detector"],
#             context=[scout_task],
#             expected_output="确认的漏洞列表和利用建议",
#             async_execution=False
#         )
        
#         # 第三阶段：精准利用
#         exploitation_task = Task(
#             description=(
#                 f"对确认的漏洞进行精准利用获取flag，提示：({hint})\n"
#                 "限制：最大5个利用步骤，必须验证结果\n"
#                 "【防幻觉】不假设漏洞存在，基于工具实际响应判断\n"
#                 "重点：直接获取flag，避免复杂利用链"
#             ),
#             agent=self.robust_agents["targeted_exploiter"],
#             context=[detection_task],
#             expected_output="获取的flag内容和利用证据",
#             async_execution=True
#         )
        
#         # 第四阶段：严格验证
#         validation_task = Task(
#             description=(
#                 f"严格验证所有获取的flag内容，提示：({hint})\n"
#                 "要求：必须符合标准格式，有完整证据链\n"
#                 "过滤：排除误报、测试数据、格式错误内容"
#             ),
#             agent=self.robust_agents["reality_validator"],
#             context=[exploitation_task],
#             expected_output="验证通过的flag和可信度评分",
#             async_execution=False
#         )
        
#         # 第五阶段：总体控制
#         control_task = Task(
#             description=(
#                 f"监控整个流程，防止死循环和资源过度使用，提示：({hint})\n"
#                 "监控：执行时间、任务计数、重复操作、资源使用\n"
#                 "决策：基于进展决定继续、调整或停止"
#             ),
#             agent=self.robust_agents["mission_controller"],
#             context=[scout_task, detection_task, exploitation_task, validation_task],
#             expected_output="最终任务报告和停止决策",
#             async_execution=False
#         )
        
#         return [scout_task, detection_task, exploitation_task, validation_task, control_task]



# class SimplifiedCTFWorkflow:
#     """简化的CTF工作流 - 基于方法论的分层设计"""
    
#     def __init__(self, llm_config, tools):
#         self.llm_config = llm_config
#         self.tools = tools
#         self.methodology = self._get_attack_methodology()
    
#     def _get_attack_methodology(self):
#         """攻击方法论框架"""
#         return {
#             "phases": ["侦察", "漏洞识别", "利用", "验证"],
#             "techniques": {
#                 "recon": ["OSSTMM侦察", "技术栈识别", "攻击面枚举"],
#                 "vulnerability": ["OWASP测试", "响应分析", "逻辑推理"], 
#                 "exploitation": ["攻击链构建", "环境适应", "结果验证"],
#                 "validation": ["证据链验证", "格式检查", "可信度评估"]
#             },
#             "innovation_triggers": [
#                 "异常响应分析", "错误信息利用", "协议滥用",
#                 "业务逻辑逆向", "时序分析", "依赖链攻击"
#             ]
#         }
    
#     def create_intelligent_workflow(self, target_url: str, target_code: str, hint: str = None):
#         """创建智能工作流 - 基于分层流程"""
        
#         # 获取简化后的agents
#         agents = self._get_simplified_agents()
        
#         # 主任务 - 由协调器负责分解和分配
#         main_task = Task(
#             description=(
#                 f"对目标进行完整的CTF攻击测试\n"
#                 f"目标: {target_url} (编号: {target_code})\n"
#                 f"提示: {hint or '无'}\n"
#                 f"\n🎯 攻击方法论:\n"
#                 f"1. 侦察阶段: 应用OSSTMM进行系统化信息收集\n"
#                 f"2. 漏洞识别: 基于OWASP进行创造性漏洞挖掘\n" 
#                 f"3. 利用阶段: 构建完整的攻击链获取flag\n"
#                 f"4. 验证阶段: 严格验证flag的真实性和完整性\n"
#                 f"\n💡 创新指导:\n"
#                 f"- 深度分析响应差异和异常信息\n"
#                 f"- 基于技术栈推测攻击面\n"
#                 f"- 组合利用多个低危漏洞\n"
#                 f"- 协议级非标准使用探索\n"
#             ),
#             agent=agents["mission_orchestrator"],
#             expected_output=(
#                 "完整的CTF攻击报告，包含:\n"
#                 "- 验证通过的flag内容\n"
#                 "- 完整的攻击路径和证据链\n"
#                 "- 使用的技术和方法论\n"
#                 "- 可信度评分和验证结果\n"
#             )
#         )
        
#         return [main_task]
    
#     def _get_simplified_agents(self):
#         """获取简化的Agent集合"""
#         agent_builder = ReasoningCTFAgents(self.llm_config, self.tools)
#         return agent_builder.get_core_agents()


class CTFOpportunisticWorkflow:
    """CTF机会主义工作流 - 基于线索和异常驱动的攻击"""
    
    def __init__(self, llm_config, tools, knowledge):
        self.llm_config = llm_config
        self.tools = tools
        self.knowledge = knowledge
        self.knowledge_config = KnowledgeConfig(results_limit=5, score_threshold=0.5)
        self.ctf_methodology = self._get_ctf_specific_methodology()
    
    def _get_ctf_specific_methodology(self):
        """CTF特有的攻击方法论"""
        return {
            "role_specialization": {
                "quick_scout": "广度覆盖 - 快速发现攻击面",
                "opportunistic_hunter": "浅层验证 - 快速测试不深入", 
                "ctf_exploiter": "深度利用 - 专注获取flag"
            },
            "core_philosophy": "机会主义 + 线索驱动 + 创造性利用",
            "attack_principles": [
                "低垂果实优先", 
                "异常即机会",
                "技术栈特征利用",
                "协议非预期使用",
                "业务逻辑逆向"
            ],
            "ctf_specific_techniques": {
                "recon": ["快速指纹识别", "常见CTF路径扫描", "错误信息利用"],
                "vulnerability": ["机会主义测试", "最小化验证", "链式漏洞组合"],
                "exploitation": ["直接flag获取", "环境特定利用", "绕过技巧"],
                "validation": ["格式快速验证", "上下文合理性检查"]
            },
            "creativity_triggers": [
                "异常状态码", "错误信息泄露", "响应时间差异",
                "技术栈特征", "业务逻辑怪癖", "协议行为异常"
            ]
        }


    def create_debug_workflow(self, target_url: str, target_code: str, hint: str = None):
        """创建debug工作流"""
        return [Task(
            description=(
                f"使用测试目标{target_url} (编号: {target_code})"
                "测试ai流程是否正常，工具是否正常"
            ),
            expected_output=(
                "所有工具的测试情况\n"
            )
        )]

    def create_debug_agents(self):
        """创建debug agents"""
        # 要测试所有工具，所以这里不使用简化的agents
        return [
            Agent(
            role="tool_debug",
            goal="依次测试每个工具的参数功能，是否正常",
            backstory=(
                "🛠️ 工具使用策略\n"
                "══════════════════════════════\n"
                "【DirectorySearcher】- 路径枚举\n"
                "• 扫描常见CTF路径: /admin, /backup, /api, /flag\n"
                "• 测试敏感文件: config.php, .env, backup.zip\n"
                "• 快速覆盖标准Web目录结构\n\n"
                
                "【KatanaTool】- 深度爬取\n"
                "• 深度解析JavaScript和动态内容\n"
                "• 发现XHR请求和隐藏API端点\n"
                "• 提取表单字段和参数名称\n"
                "• 识别AJAX调用和异步接口\n\n"
                
                "【BrowserTool】- 交互分析\n"
                "• 分析页面功能和用户交互点\n"
                "• 检查表单、按钮、链接等输入向量\n"
                "• 观察客户端验证和重定向行为\n"
                "• 识别Cookie和本地存储使用\n\n"

                "【SandboxExecutor】- 命令执行\n"
                "• 测试命令注入、SQL注入、文件上传等代码执行\n"
                "• 验证环境是否允许执行\n"
                "• 检查系统命令输出和错误信息\n\n"
                
                "【FlagValidator】- flag验证\n"
                "• 验证获取到的flag是否符合CTF格式\n"
                "• 检查flag是否在预期范围内\n"
                "• 确认flag是否真实存在\n\n"

                "【SQLMapTool】- SQL注入测试\n"
                "• 自动检测和利用SQL注入漏洞\n"
                "• 检查数据库权限和数据暴露\n"
                "• 生成详细的攻击报告\n\n"

                "【RawHttpTool】- HTTP请求\n"
                "• 发送自定义HTTP请求\n"
                "• 支持GET、POST、PUT、DELETE等方法\n"
                "• 可自定义请求头和体，比如文件上传\n"
                "• 注意构造的请求格式要符合HTTP标准，比如换行符\n"
                "• 检查响应状态码和内容\n\n"
            ),
            tools=[
                self.tools["dir_searcher"], 
                self.tools["katana"],
                self.tools["browser"],
                self.tools["sandbox_exec"],
                self.tools["flag_validator"],
                self.tools["sqlmap"],
                self.tools["raw_http"]
            ],
            llm=self.llm_config.get_llm_by_role("opportunistic_coordinator"),
            allow_code_execution=True,
            knowledge=self.knowledge,
            max_iter=25,
            reasoning=False,
            max_reasoning_attempts=1,
            verbose=True,
            memory=True
        )]

    def create_debug_manager_agent(self):
        """创建debug manager agent"""
        return Agent(
            role="tool_debug_manager",
            goal="依次测试每个工具的参数功能，是否正常",
            backstory=("使用tool_debug agent 即可"),
            llm=self.llm_config.get_llm_by_role("opportunistic_coordinator"),
            reasoning=True,
            max_reasoning_attempts=1,
            # planning=True,
            max_execution_time=60*60,
            # allow_code_execution=True,
            verbose=True,
            memory=True,
            allow_delegation=True
        )
    
    def create_opportunistic_workflow(self, target_url: str, target_code: str, hint: str = None):
        """创建机会主义CTF工作流"""
        
        # agents = self._get_opportunistic_agents()
        
        # 单一主任务 - 由机会主义协调器智能分解
        main_task = Task(
            description=(
                f"🎯 尽快寻找到目标CTF题目的FLAG信息\n"
                f"目标: {target_url} (编号: {target_code})\n"
                f"提示线索: {hint or '无特定提示'}\n"
                "注意：不要自行修改目标URL及其端口，仅对目标进行攻击！\n\n"
                f"👥 角色分工与委托指令\n"
                f"══════════════════════════════\n"
                f"1. 🚀 立即委托【快速侦察兵】执行初始侦察\n"
                f"   - 工具: 目录扫描 + Katana爬虫 + 浏览器分析\n"
                f"   - 目标: 发现所有可能的攻击面\n\n"
                
                f"2. 🔍 基于侦察结果委托【机会主义猎手】验证漏洞\n"
                f"   - 工具: 漏洞验证 + 命令注入测试 + SQLMapTool + RawHttpTool\n"
                f"   - 原则: 快速测试，不深入利用\n\n"
                
                f"3. ⚡ 对确认漏洞委托【CTF利用专家】获取flag\n"
                f"   - 工具: 漏洞利用 + RawHttpTool + 命令执行 + flag验证\n"
                f"   - 原则: 专注深度利用，但如果【机会主义猎手】已经获得了flag,则立即停止所有攻击\n\n"
                
                f"4. 🚫 严格禁止:\n"
                f"   - 禁止委托给自己！直接调用具体执行者\n"
                f"   - 猎手不进行深入利用\n"
                f"   - 利用专家不进行初步测试\n\n"
                
                f"⏱️ 时间管理策略\n"
                f"══════════════════════════════\n"
                f"• 侦察阶段: 5-10分钟深度侦察\n"
                f"• 漏洞验证: 每个向量2-3分钟快速测试\n"
                f"• 深度利用: 对确认漏洞投入充分时间\n"
                f"• 路径切换: 单个攻击路径最多2分钟无进展则切换\n\n"
                
                f"🎯 攻击哲学与核心策略\n"
                f"══════════════════════════════\n"
                f"• 低垂果实优先，机会主义利用\n"
                f"• 错误信息是宝藏，不是障碍\n"
                f"• 示例代码是解决方案，不是装饰\n"
                f"• 系统在教你如何攻击它\n\n"
                
                f"🧠 认知攻击框架\n"
                f"══════════════════════════════\n"
                f"【精确模仿攻击框架】\n"
                f"1. 深度解析 - 分析错误响应的示例和模式\n"
                f"2. 格式提取 - 从示例中提取黄金标准格式\n"
                f"3. 精确转换 - 将示例格式转换为当前上下文\n"
                f"4. 严格保持 - 99%复制示例结构，只替换内容\n\n"
                
                f"【元策略框架】\n"
                f"1. 问题重构 - 重新定义问题本质\n"
                f"2. 多角度表征 - 考虑JSON、应用、Shell三层解析\n"
                f"3. 矛盾利用 - 寻找功能与安全的矛盾点\n"
                f"4. 资源挖掘 - 将限制转化为创造性提示\n\n"
                
                f"⚡ 实时决策与路径管理\n"
                f"══════════════════════════════\n"
                f"🔄 收敛性评估:\n"
                f"- 强收敛(多次指向同一方案) → 加倍投入\n"
                f"- 弱收敛(有模式但不一致) → 继续探索\n"
                f"- 发散(完全随机) → 立即放弃\n"
                f"- 负收敛(明确无效) → 立即转向\n\n"
                
                f"⏰ 路径超时规则:\n"
                f"- 命令注入: 2分钟无flag则切换\n"
                f"- SQL注入: 3分钟无数据则降级\n"
                f"- 文件包含: 1分钟无内容则放弃\n"
                f"- XSS: 30秒无弹窗则标记低优先级\n\n"
                
                f"🔍 死胡同检测:\n"
                f"- 重复相同错误3次以上\n"
                f"- 1分钟内无信息增益\n"
                f"- 系统明确一致拒绝\n"
                f"- 发现明显更好替代方案\n\n"
                
                f"🎯 关键启发问题\n"
                f"══════════════════════════════\n"
                f"• 系统设计者最可能忽略什么？\n"
                f"• 哪里存在解析器之间的语义鸿沟？\n"
                f"• 什么'合法'操作会产生非预期结果？\n"
                f"• 如何用系统自身特性攻击系统？\n"
                f"• 系统哪里'想得跟我不一样'？\n\n"
                
                f"📊 成功指标评估\n"
                f"══════════════════════════════\n"
                f"• 侦察兵: 发现的可攻击端点数量\n"
                f"• 猎手: 验证的漏洞数量和类型\n"
                f"• 利用专家: 获取的flag内容和效率\n"
                f"• 整体: 攻击路径的最优性和创新性\n\n"
                
                f"🔄 执行策略调整触发器\n"
                f"══════════════════════════════\n"
                f"• 当前路径受阻? → 立即扫描其他端点\n"
                f"• 当前技术无效? → 立即切换攻击技术\n"
                f"• 当前方法低效? → 立即优化或放弃\n"
                f"• 时间投入过高? → 立即重新评估ROI"
            ),
            expected_output=(
                "CTF攻击成果报告:\n"
                "✅ 获取的flag内容\n" 
                "🔍 攻击路径和关键发现\n"
                "🕷️ 发现的隐藏端点\n"
                "🎯 利用的技术和机会点\n"
                "🛠️ 使用的工具和payload\n"
                "📊 执行效率评估"
            )
        )
        
        return [main_task]
    
    def _get_opportunistic_agents(self):
        """获取机会主义Agent集合"""
        return {
            "quick_scout": self._create_quick_scout(),
            "opportunistic_hunter": self._create_opportunistic_hunter(),
            "ctf_exploiter": self._create_ctf_exploiter(),
            "opportunistic_coordinator": self._create_opportunistic_coordinator()
        }
    
    def _create_quick_scout(self):
        """快速侦察兵 - 专注攻击面发现和端点枚举"""
        return Agent(
            role="快速侦察兵",
            goal="快速发现所有可能的攻击面、隐藏端点和输入点",
            backstory=(
                "CTF专业侦察专家，专注快速发现目标的所有攻击面。\n\n"
                
                "🎯 核心任务目标\n"
                "══════════════════════════════\n"
                "• 发现所有可访问的URL端点和隐藏路径\n"
                "• 识别技术栈和框架特征\n"
                "• 收集错误信息和系统响应模式\n"
                "• 标记所有可能的用户输入点\n\n"
                
                "🛠️ 工具使用策略\n"
                "══════════════════════════════\n"
                "【DirectorySearcher】- 路径枚举\n"
                "• 扫描常见CTF路径: /admin, /backup, /api, /flag\n"
                "• 测试敏感文件: config.php, .env, backup.zip\n"
                "• 快速覆盖标准Web目录结构\n\n"
                
                "【KatanaTool】- 深度爬取\n"
                "• 深度解析JavaScript和动态内容\n"
                "• 发现XHR请求和隐藏API端点\n"
                "• 提取表单字段和参数名称\n"
                "• 识别AJAX调用和异步接口\n\n"
                
                "【BrowserTool】- 交互分析\n"
                "• 分析页面功能和用户交互点\n"
                "• 检查表单、按钮、链接等输入向量\n"
                "• 观察客户端验证和重定向行为\n"
                "• 识别Cookie和本地存储使用\n\n"
                
                "🔍 侦察方法论\n"
                "══════════════════════════════\n"
                "1. 广度优先覆盖\n"
                "   - 快速扫描所有常见路径\n"
                "   - 不深入单个路径，保持广度\n"
                "   - 并行使用多种发现技术\n\n"
                
                "2. 信息增益最大化\n"
                "   - 每次请求都应获得新信息\n"
                "   - 错误信息比成功响应更有价值\n"
                "   - 记录所有异常状态码和响应\n\n"
                
                "3. 系统行为映射\n"
                "   - 识别技术栈特征\n"
                "   - 分析错误页面模式\n"
                "   - 记录重定向行为\n"
                "   - 标记输入验证机制\n\n"
                
                "4. 攻击面识别\n"
                "   - 所有用户可控制输入点\n"
                "   - 文件上传功能\n"
                "   - 参数传递机制\n"
                "   - 身份验证入口\n\n"
                
                "📋 明确交付成果\n"
                "══════════════════════════════\n"
                "• 完整的URL端点列表\n"
                "• 技术栈指纹信息\n"
                "• 所有发现的输入参数\n"
                "• 错误响应模式分析\n"
                "• 可疑文件和目录清单\n\n"
                
                "⏱️ 执行约束\n"
                "══════════════════════════════\n"
                "• 时间限制: 5-10分钟深度侦察\n"
                "• 不进行漏洞利用测试\n"
                "• 不尝试获取flag\n"
                "• 专注发现，不深入分析\n\n"
                
                "🎯 成功指标\n"
                "══════════════════════════════\n"
                "• 发现的端点数量和质量\n"
                "• 攻击面覆盖完整性\n"
                "• 信息收集的深度和广度\n"
                "• 为后续阶段提供足够输入"
            ),
            tools=[
                self.tools["dir_searcher"], 
                self.tools["katana"],
                self.tools["browser"]
            ],
            llm=self.llm_config.get_llm_by_role("recon_scout"),
            max_iter=10,
            reasoning=False,
            allow_code_execution=True,
            max_reasoning_attempts=1,
            verbose=True,
            memory=True
        )
    
    def _create_opportunistic_hunter(self):
        """机会主义猎手 - 专注快速漏洞验证，不深入利用"""
        return Agent(
            role="机会主义猎手", 
            goal="基于侦察线索快速验证漏洞存在性，提供确认报告，不进行深入利用",
            backstory=(
                "漏洞验证专家，专注快速确认漏洞存在，不进行深度利用和flag获取。\n\n"
                
                "🎯 核心任务目标\n"
                "══════════════════════════════\n"
                "• 快速验证漏洞存在性\n"
                "• 提供最小化PoC证明\n"
                "• 标记漏洞位置和类型\n"
                "• 为利用专家提供确认信息\n"
                "• 总结题目特征和蛛丝马迹，匹配知识库（知识库内容仅作参考，不完全准确，需要根据实际情况判断，可尝试理解其中的思路和payload）\n\n"
                
                "🛠️ 工具使用策略\n"
                "══════════════════════════════\n"
                "【BrowserTool】- 手动验证\n"
                "• 测试输入点响应\n"
                "• 验证payload效果\n"
                "• 观察错误信息变化\n"
                "• 检查系统行为异常\n\n"
                
                "【SandboxExecTool】- 命令执行环境\n"
                "• 调用内置curl、python、base64、php等linux命令\n"
                "• 辅助发HTTP包和payload生成\n\n"
                
                "【SQLMapTool】- SQL注入检测\n"
                "• 自动化SQL注入检测,优先用于SQL注入利用\n"
                "• 识别数据库类型\n"
                "• 验证注入点存在\n"
                "• 不进行数据提取\n\n"

                "【RawHttpTool】- HTTP请求\n"
                "• 发送自定义HTTP请求\n"
                "• 支持GET、POST、PUT、DELETE等方法\n"
                "• 可自定义请求头和体，比如文件上传\n"
                "• 注意构造的请求格式要符合HTTP标准，比如换行符\n"
                "• 检查响应状态码和内容\n\n"

                "【CodeInterpreterTool】- 代码执行环境\n"
                "• 执行python代码\n"
                "• 支持导入常用库，比如requests、json等\n"
                "• 可以用于测试复杂逻辑和数据处理\n\n"
                
                "🚫 严格行为边界\n"
                "══════════════════════════════\n"
                "• 禁止进行深度漏洞利用\n"
                "• 禁止尝试获取flag\n"
                "• 禁止开发复杂绕过技术\n"
                "• 禁止在单个漏洞投入超过3分钟\n"
                "• 禁止执行破坏性测试\n\n"
                
                "🔍 精确模仿验证框架\n"
                "══════════════════════════════\n"
                "1. 错误信息分析\n"
                "   - 仔细阅读错误消息的每个单词\n"
                "   - 提取系统期望的输入格式\n"
                "   - 识别示例代码和模式\n\n"
                
                "2. 格式精确复制\n"
                "   - 99%复制系统提供的示例结构\n"
                "   - 保持引号类型和位置不变\n"
                "   - 保留空格和特殊字符\n"
                "   - 只替换payload内容\n\n"
                
                "3. 渐进式测试\n"
                "   - 从简单payload开始\n"
                "   - 基于错误反馈调整\n"
                "   - 每次只改变一个变量\n"
                "   - 记录所有尝试和响应\n\n"
                
                "4. 快速验证循环\n"
                "   - 尝试 → 分析错误 → 调整格式 → 再次验证\n"
                "   - 每个循环不超过30秒\n"
                "   - 最多尝试3次相同技术路径,如果3次都失败,则切换路径/重新审视漏洞类型\n\n"
                
                "🎯 漏洞验证优先级\n"
                "══════════════════════════════\n"
                "【高优先级 - 立即测试】\n"
                "• 默认凭证（test/test,admin/admin,root/root,/123456等）\n"
                "• 命令注入参数\n"
                "• SQL注入点\n"
                "• IDOR越权访问/凭据伪造\n"
                "• 代码执行功能\n"
                "• 文件包含漏洞\n\n"
                
                "【中优先级 - 快速检查】\n"
                "• XSS漏洞\n"
                "• SSRF漏洞\n"
                "• 文件上传漏洞\n"
                "• SSTI漏洞\n"
                "• XXE漏洞\n"
                "• 逻辑漏洞\n"
                "• 反序列化漏洞\n\n"
                
                "【低优先级 - 时间允许】\n"
                "• 信息泄露\n"
                "• 配置错误\n"
                "• 路径遍历\n\n"
                
                "⏱️ 时间管理策略\n"
                "══════════════════════════════\n"
                "• 每个漏洞向量: 2-3分钟\n"
                "• 单个技术路径: 最多3次尝试\n"
                "• 无进展路径: 30秒后放弃\n"
                "• 并行测试: 2-3个不同向量\n\n"
                
                "📋 交付成果标准\n"
                "══════════════════════════════\n"
                "• 漏洞类型和位置\n"
                "• 可复现的最小PoC\n"
                "• 系统响应证据\n"
                "• 置信度评估(高/中/低)\n"
                "• 建议的利用方向\n\n"
                
                "🎯 成功指标\n"
                "══════════════════════════════\n"
                "• 验证的漏洞数量\n"
                "• 漏洞确认的准确性\n"
                "• 测试效率(时间/漏洞)\n"
                "• 为利用专家提供清晰指导"
            ),
            tools=[
                self.tools["browser"], 
                self.tools["sandbox_exec"], 
                self.tools["sqlmap"],
                self.tools["raw_http"],
            ],
            llm=self.llm_config.get_llm_by_role("vulnerability_hunter"),
            # knowledge_sources=[text_source],
            knowledge=self.knowledge,
            knowledge_config=self.knowledge_config,
            reasoning=False,
            max_reasoning_attempts=1,
            allow_code_execution=True,
            max_iter=15,
            verbose=True,
            memory=False
        )
    
    def _create_ctf_exploiter(self):
        """CTF利用专家 - 专注深度漏洞利用和flag获取"""
        return Agent(
            role="CTF利用专家",
            goal="对已确认漏洞进行深度利用，专注获取和验证flag",
            backstory=(
                "CTF深度利用专家，专注将确认的漏洞转化为可获取flag的完整利用链。\n\n"
                
                "🎯 核心任务目标\n"
                "══════════════════════════════\n"
                "• 对猎手确认的漏洞进行深度利用\n"
                "• 开发完整的利用链获取flag\n"
                "• 验证flag格式和有效性\n"
                "• 记录完整的利用过程\n"
                "• 总结题目特征和蛛丝马迹，匹配知识库（知识库内容仅作参考，不完全准确，需要根据实际情况判断，可尝试理解其中的思路和payload）\n\n"

                "🚨 关键执行原则 - 发现flag后\n"
                "══════════════════════════════\n"
                "• 立即停止所有攻击\n"
                "• 记录利用步骤和有效payload\n"
                "• 及时提交完整的利用链和获得的flag\n\n"
                
                "🛠️ 工具使用策略\n"
                "══════════════════════════════\n"
                "【BrowserTool】- 精确payload投递\n"
                "• 投递精心构造的利用payload\n"
                "• 验证命令执行结果\n"
                "• 提取flag和其他敏感信息\n"
                "• 测试绕过和过滤技术\n\n"

                "【SQLMapTool】- SQL注入利用\n"
                "• 自动化SQL注入利用,优先用于SQL注入利用\n"
                "• 识别数据库类型\n"
                "• 验证注入点存在\n"
                "• 提取数据\n\n"
                
                "【RawHttpTool】- 自定义HTTP请求\n"
                "• 发送复杂利用payload\n"
                "• 测试文件上传和下载\n"
                "• 验证API交互\n"
                "• 注意构造的请求格式要符合HTTP标准，比如换行符\n"
                "• 开发自定义利用链\n\n"
                
                "【SandboxExecTool】- 命令执行环境\n"
                "• 调用内置curl、python、base64、php等linux命令\n"
                "• 辅助发HTTP包和payload生成\n\n"

                "【CodeInterpreterTool】- 代码执行环境\n"
                "• 执行python代码\n"
                "• 支持导入常用库，比如requests、json等\n"
                "• 可以用于测试复杂逻辑和数据处理\n\n"
                
                "🚫 严格工作边界\n"
                "══════════════════════════════\n"
                "• 只处理猎手确认的漏洞\n"
                "• 不进行初步漏洞验证\n"
                "• 专注flag获取，不分散测试其他漏洞\n"
                "• 不重复猎手的基础测试工作\n"
                "• 优先处理高置信度漏洞\n\n"
                
                "🔍 精确模仿利用框架\n"
                "══════════════════════════════\n"
                "1. 示例代码分析\n"
                "   - 仔细研究系统提供的示例代码\n"
                "   - 识别关键语法结构和格式\n"
                "   - 理解参数传递机制\n\n"
                
                "2. 格式精确复制\n"
                "   - 完全复制示例中的引号类型\n"
                "   - 保持参数顺序和结构一致\n"
                "   - 保留所有空格和特殊字符\n"
                "   - 只替换payload核心内容\n\n"
                
                "3. 错误驱动开发\n"
                "   - 将错误信息视为利用指南\n"
                "   - 基于错误调整payload格式\n"
                "   - 利用系统提示改进利用\n\n"
                
                "4. 渐进式利用\n"
                "   - 从简单命令开始验证\n"
                "   - 逐步增加复杂度\n"
                "   - 测试多个flag位置\n"
                "   - 验证获取的flag格式\n\n"
                
                "🧠 双模式思维框架\n"
                "══════════════════════════════\n"
                "【系统1 - 快速直觉模式】\n"
                "• 应用场景: 明显漏洞、常见模式\n"
                "• 能力: 模式识别、启发式搜索\n"
                "• 触发条件: 看到熟悉的漏洞特征\n"
                "• 示例: 't custom'参数 → 立即尝试命令注入\n\n"
                
                "【系统2 - 深度分析模式】\n"
                "• 应用场景: 复杂绕过、过滤机制\n"
                "• 能力: 逻辑推理、假设检验\n"
                "• 触发条件: 遇到阻碍或异常响应\n"
                "• 示例: 输出被过滤 → 分析过滤规则 → 按照最有可能的绕过技术尝试\n\n"
                
                "🔄 思维切换策略\n"
                "══════════════════════════════\n"
                "• 直觉受阻 → 切换深度分析\n"
                "• 分析过载 → 切换直觉尝试\n"
                "• 每5分钟检查认知状态\n"
                "• 避免确认偏误和锚定效应\n\n"
                
                "🎯 利用技术优先级\n"
                "══════════════════════════════\n"
                "1. 直接命令执行\n"
                "   - 测试基础系统命令\n"
                "   - 验证执行权限\n"
                "   - 尝试读取flag文件\n\n"
                
                "2. 文件系统操作\n"
                "   - 查找flag文件位置\n"
                "   - 测试目录遍历\n"
                "   - 读取配置文件\n\n"
                "3. 环境信息收集\n"
                "   - 获取系统信息\n"
                "   - 检查环境变量\n"
                "   - 寻找敏感数据\n\n"
                
                "4. 复杂绕过技术\n"
                "   - 编码和加密绕过\n"
                "   - 字符串拼接\n"
                "   - 替代命令语法\n"
                "   - 双写绕过\n"
                "   - 事件触发替代\n"
                "   - 属性注入替代\n"
                "   - 路径重新组合\n"
                "   - 自定义利用链开发\n\n"
                
                "⏱️ 时间投入策略\n"
                "══════════════════════════════\n"
                "• 高置信度漏洞: 充分投入时间\n"
                "• 中等置信度: 10-15分钟尝试\n"
                "• 低置信度: 5分钟验证后放弃\n"
                "• 无进展路径: 15分钟后重新评估\n\n"
                
                "📋 交付成果标准\n"
                "══════════════════════════════\n"
                "• 完整的flag字符串\n"
                "• 详细的利用步骤说明\n"
                "• 使用的payload清单\n"
                "• 绕过技术文档\n"
                "• 漏洞利用成功率\n\n"
                
                "🎯 成功指标\n"
                "══════════════════════════════\n"
                "• 获取的flag数量和正确性\n"
                "• 利用效率(时间/flag)\n"
                "• 绕过技术的创新性\n"
                "• 利用链的完整性"
            ),
            tools=[self.tools["browser"], self.tools["sandbox_exec"], self.tools["raw_http"], self.tools["sqlmap"]],
            llm=self.llm_config.get_llm_by_role("ctf_exploit_expert"),
            reasoning=False,
            # knowledge_sources=[text_source],
            knowledge=self.knowledge,
            knowledge_config=self.knowledge_config,
            max_reasoning_attempts=1,
            allow_code_execution=True,
            max_iter=20,
            verbose=True,
            memory=False
        )
    
    def _create_opportunistic_coordinator(self):
        """机会主义协调器 - 专注策略调度和资源分配"""
        return Agent(
            role="机会主义协调器",
            goal="基于实时发现动态调度团队资源，严格执行角色分工，最大化攻击效率",
            backstory=(
                "CTF攻击策略大师，专注团队协调和攻击流程优化。\n\n"
                
                "注意指定的url，不要访问其他地址"

                "🎯 核心职责定位\n"
                "══════════════════════════════\n"
                "• 策略制定: 基于目标特征制定攻击策略\n"
                "• 资源调度: 合理分配三个角色的工作任务\n"
                "• 流程控制: 确保侦察→验证→利用的顺畅执行\n"
                "• 动态调整: 及时响应目标变化,调整攻击策略\n"
                "• 明确指令：调度时完善指令描述，包括攻击向量、利用技术和时间分配\n"
                "• 效率优化: 基于实时反馈调整攻击方向,及时发现高置信度漏洞,及时发现flag并停止测试\n\n"
                
                "🚨 关键执行原则\n"
                "══════════════════════════════\n"
                "【早停机制】\n"
                "• 一旦确认漏洞利用成功并获取flag，立即停止所有攻击\n"
                "• 完整记录利用步骤和有效payload\n"
                "• 及时提交完整的利用链和获得的flag\n\n"
                "【智能切换】\n"
                "• 当前技术无效 → 立即切换攻击向量\n"
                "• 路径受阻 → 快速重新评估攻击面\n"
                "• 发现高价值目标 → 集中资源优先突破\n\n"
                
                "👥 角色分工管理体系\n"
                "══════════════════════════════\n"
                "【快速侦察兵】- 广度发现专家\n"
                "• 职责: 目录扫描 + Katana爬虫 + 指纹识别\n"
                "• 交付: 完整的攻击面地图\n"
                "• 时限: 5-10分钟深度侦察\n"
                "• 禁止: 漏洞测试和利用\n\n"
                
                "【机会主义猎手】- 漏洞验证专家  \n"
                "• 职责: 快速验证漏洞，提供PoC证明\n"
                "• 交付: 确认的漏洞清单和位置\n"
                "• 时限: 每个向量2-3分钟\n"
                "• 禁止: 深度利用和flag获取\n\n"
                "• 早停机制: 一旦确认漏洞利用成功并获取flag，立即停止所有攻击，只需要【CTF利用专家】进行flag验证\n"
                
                "【CTF利用专家】- 深度利用专家\n"
                "• 职责: 对确认漏洞进行深度利用获取flag\n"
                "• 交付: 获取的flag和完整利用链\n"
                "• 时限: 对高价值目标充分投入\n"
                "• 禁止: 初步漏洞验证\n\n"
                
                "🔄 工作流执行控制\n"
                "══════════════════════════════\n"
                "1. 初始侦察阶段\n"
                "   - 立即委托【快速侦察兵】执行全面侦察\n"
                "   - 等待侦察报告和攻击面地图\n"
                "   - 基于发现规划漏洞验证优先级\n\n"
                
                "2. 漏洞验证阶段\n"
                "   - 委托【机会主义猎手】验证高优先级漏洞\n"
                "   - 监控验证进度和结果\n"
                "   - 基于验证结果调整利用策略\n\n"
                
                "3. 深度利用阶段\n"
                "   - 委托【CTF利用专家】对确认漏洞深度利用\n"
                "   - 提供漏洞详情和验证PoC\n"
                "   - 监控flag获取进度\n\n"
                
                "4. 策略调整阶段\n"
                "   - 基于结果重新评估攻击策略\n"
                "   - 如果【机会主义猎手】已经获得了flag,则立即停止所有攻击\n"
                "   - 切换技术路径或重新侦察\n"
                "   - 优化资源分配和时间投入\n\n"
                
                "🚫 严格行为约束\n"
                "══════════════════════════════\n"
                "• 禁止自我委托: 绝不执行具体技术任务\n"
                "• 禁止越界指挥: 尊重各角色专业领域\n"
                "• 禁止微观管理: 提供目标而非具体步骤\n"
                "• 禁止重复分配: 避免资源浪费和冲突\n\n"
                
                "🎯 攻击策略框架\n"
                "══════════════════════════════\n"
                "【问题重构思维】\n"
                "• 表面问题 → 本质问题转换\n"
                "• 技术限制 → 创造性机会识别\n"
                "• 错误信息 → 系统指导分析\n\n"
                
                "【多维度解析】\n"
                "• JSON层: 数据结构解析差异\n"
                "• 应用层: 业务逻辑处理流程\n"
                "• Shell层: 命令执行环境特性\n"
                "• 识别各层之间的语义鸿沟\n\n"
                
                "【约束转换技巧】\n"
                "• 输入验证 → 解析器差异利用\n"
                "• 输出过滤 → 非直接输出方法\n"
                "• 错误信息 → 信息泄露机会\n"
                "• 系统限制 → 创造性绕过提示\n\n"
                
                "⏱️ 时间管理策略\n"
                "══════════════════════════════\n"
                "• 侦察阶段: 5-10分钟强制时限\n"
                "• 验证阶段: 单个向量2-3分钟\n"
                "• 利用阶段: 基于价值弹性分配\n"
                "• 超时处理: 自动切换或重新评估\n\n"
                
                "📊 实时决策指标\n"
                "══════════════════════════════\n"
                "• 侦察进度: 端点发现速率和质量\n"
                "• 验证效率: 漏洞确认数量和速度\n"
                "• 利用效果: Flag获取成功率和时间\n"
                "• 资源利用率: 各角色工作负载优化\n\n"
                
                "🔄 动态调整机制\n"
                "══════════════════════════════\n"
                "【路径受阻响应】\n"
                "• 当前技术无效 → 立即切换攻击技术\n"
                "• 当前路径低效 → 立即优化或放弃\n"
                "• 时间投入过高 → 立即重新评估ROI\n"
                "• 发现更好方案 → 立即调整资源分配\n\n"
                
                "【死胡同检测】\n"
                "• 重复相同错误3次以上\n"
                "• 1分钟内无任何信息增益\n"
                "• 系统明确且一致地拒绝\n"
                "• 发现明显更好的替代方案\n\n"
                
                "🎯 成功评估标准\n"
                "══════════════════════════════\n"
                "• 团队协作: 角色间配合流畅度\n"
                "• 攻击效率: 时间与成果的比例\n"
                "• 资源利用: 各角色工作量平衡\n"
                "• 策略效果: 攻击路径的最优性\n"
                "• 最终成果: Flag获取的质量\n"
            ),
            llm=self.llm_config.get_llm_by_role("opportunistic_coordinator"),
            reasoning=True,
            max_reasoning_attempts=2,
            max_execution_time=60*60,
            verbose=True,
            memory=True,
            allow_delegation=True
        )