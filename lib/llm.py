from crewai import LLM
from crewai.llms.providers.openai.completion import OpenAICompletion
from crewai.llms.providers.anthropic.completion import AnthropicCompletion
from browser_use.llm import ChatOpenAI, ChatDeepSeek, ChatAnthropic
import os

class CrewLLMConfig:
    """LLM 配置类：根据角色类型返回 ChatOpenAI 实例"""

    cache = {}  

    def get_llm_by_role(self, role_type: str) -> LLM:
        if role_type in self.cache:
            return self.cache[role_type]

        configs = {
            "recon_scout": {"model": "deepseek-chat", "temperature": 0.15, "max_tokens": 4096},
            "vulnerability_hunter": {"model": "deepseek-chat", "temperature": 0.2, "max_tokens": 4096},
            "ctf_exploit_expert": {"model": "deepseek-chat", "temperature": 0.25, "max_tokens": 8094},
            "opportunistic_coordinator": {"model": "deepseek-reasoner", "temperature": 0.3, "max_tokens": 8094},
        }
        
        provider    = os.getenv("CREWAI_LLM_PROVIDER")
        model_name  = os.getenv("CREWAI_LLM_NAME")
        base_url    = os.getenv("CREWAI_LLM_BASE_URL")
        api_key     = os.getenv("CREWAI_LLM_API_KEY")
        stream      = os.getenv("CREWAI_LLM_STREAM", "false").lower() == "true"
        llm_timeout = int(os.getenv("LLM_TIMEOUT", "60"))
        
        cfg = configs.get(role_type, configs["vulnerability_hunter"])

        if provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
            llm = AnthropicCompletion(
                provider="anthropic",
                model=model_name or cfg["model"],
                base_url=base_url,
                api_key=api_key,
                temperature=1.0,
                max_tokens=cfg["max_tokens"],
                timeout=llm_timeout,
            )
            llm.supports_tools = True
        elif provider == "deepseek":
            llm = LLM(
                model="deepseek/" + (model_name or cfg["model"]),
                base_url=base_url,
                api_key=api_key,
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                timeout=llm_timeout,
                stream=stream,
            )
        else:
            llm = OpenAICompletion(
                model=model_name or cfg["model"],
                base_url=base_url,
                api_key=api_key,
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"],
                timeout=llm_timeout,
                stream=stream,
                # extra_body={"reasoning_split": True},
                reasoning_effort="none"
            )
        self.cache[role_type] = llm
        return llm



if os.getenv("BROWSER_MODEL_PROVIDER") == "anthropic":
    BrowserLLM = ChatAnthropic(
        model=os.getenv("BROWSER_MODEL_NAME"),
        api_key=os.getenv("BROWSER_OPENAI_KEY"),
        base_url=os.getenv("BROWSER_OPENAI_BASE_URL"),
        temperature=0.15
    )
elif os.getenv("BROWSER_MODEL_PROVIDER") == "deepseek":
    BrowserLLM = ChatDeepSeek(
        model=os.getenv("BROWSER_MODEL_NAME"),
        api_key=os.getenv("BROWSER_OPENAI_KEY"),
        base_url=os.getenv("BROWSER_OPENAI_BASE_URL"),
        temperature=0.15
    )
else:
    BrowserLLM = ChatOpenAI(
        model=os.getenv("BROWSER_MODEL_NAME"),
        api_key=os.getenv("BROWSER_OPENAI_KEY"),
        base_url=os.getenv("BROWSER_OPENAI_BASE_URL"),
        temperature=0.15,
        reasoning_models=["deepseek/deepseek-reasoner", "MiniMax-M2"],
        # reasoning_effort="none"
    )