## 框架

- 基于CrewAI的ReAct架构
- 重方法论引导的多Agent定义
- 结合ARG知识库扩展专业能力边界

## docker环境
### 浏览器
```
sh start_steel_browsers.sh
```

### sqlmap&exec
```
docker run -it -d --name sqlmap --restart=unless-stopped --entrypoint bash googlesky/sqlmap
docker exec -it sqlmap bash -c 'apt update && apt install -y hashcat php sshpass'
```

### katana
```
docker run -d -it --name katana --restart=unless-stopped --entrypoint sh projectdiscovery/katana
```

### ~~ollama~~
~~curl -fsSL https://ollama.com/install.sh | sh~~
~~ollama pull bge-m3:latest~~

### python环境
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

### 目录扫描
```
git clone https://github.com/kingkaki/ctf-wscan.git
```

### 需修改的库代码

#### browser_use
~/miniconda3/lib/python3.13/site-packages/browser_use/browser/watchdogs/security_watchdog.py:
```
self.logger.warning(f'⛔️ Navigation to non-allowed URL detected: {event.url}')

if parsed.scheme in ['data', 'blob', 'view-source']:
```

#### crewai
<!-- ~/miniconda3/lib/python3.13/site-packages/crewai/llms/providers/anthropic/completion.py -->

see https://github.com/crewAIInc/crewAI/pull/3970 (已经修复，可跳过)
```
# ~/miniconda3/lib/python3.13/site-packages/crewai/memory/storage/rag_storage.py
if self.path:
    config.settings.persist_directory = self.path
self._client = create_client(config)
```


## 运行
```
cp .env.example .env
配置好ai key

python main.py --url http://xxx

## 清除crewai缓存
rm -rf ../../.local/share/newmapta/
rm -rf ../../.local/share/ctf_*
```

## note
- 不同的模型可能需要不同的temperature参数,在`lib/llm.py`中定义