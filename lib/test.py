from dotenv import load_dotenv
load_dotenv()
from tools import RawHttpTool, SQLMapTool, KatanaTool, BrowserTool, SandboxExecTool, FlagValidatorTool



def test_raw_http_tool(url: str):
    tool = RawHttpTool()
    k = {                                                                                                                           
        "url": url,                                                                            
        "raw_request": "GET /index.php HTTP/1.1\r\nHost: 127.0.0.1\r\nCookie: 1=1\r\n\r\n",          
        "timeout": 10,            
        "start_response_index": 0,
        "end_response_index": 10000,
        "redirect": False,                                                                                      
    }                                                                                                                           
                                                                                
                         
    result = tool.run(**k)
    print(result)


def test_sqlmap_tool(url: str):
    tool = SQLMapTool()
    k = {
        "target_url": url,
        "action": "detect",
        "extra_params": "--batch --level=3 --risk=2"
    }
    result = tool.run(**k)
    print(result)

def test_katana_tool(url: str):
    tool = KatanaTool()
    k = {
        "target_url": url,
    }
    result = tool.run(**k)
    print(result)

def test_browser_tool(url: str):
    tool = BrowserTool()
    k = {
        "task_description": f"访问 {url} 设置cookie ab=123,获取页面cookie",
        "max_steps": 10,
    }   
    result = tool.run(**k)
    print(result)

def test_sandbox_exec_tool():
    tool = SandboxExecTool()
    k = {
        "command": "ls -l",
    }
    result = tool.run(**k)
    print(result)

def test_flag_validator_tool():
    tool = FlagValidatorTool()
    k = {
        "content": "CTF{1234567890}",
    }
    result = tool.run(**k)
    print(result)

if __name__ == "__main__":
    # test_katana_tool("https://example.com/")
    test_browser_tool("https://example.com/")
    # test_sandbox_exec_tool()
    # test_flag_validator_tool()
    # test_raw_http_tool()
    # test_sqlmap_tool()
