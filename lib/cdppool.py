import logging
import asyncio
from typing import Dict, List, Any
from contextlib import asynccontextmanager

class CDPConnectionPool:
    """CDP URL 连接池 - 线程安全"""
    
    def __init__(self, cdp_urls: List[str]):
        self.cdp_urls = cdp_urls
        self.available_urls = asyncio.Queue()
        self.in_use_urls: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
        
        # 初始化可用URL队列
        for url in cdp_urls:
            self.available_urls.put_nowait(url)
            self.in_use_urls[url] = False
        
        self.logger = logging.getLogger("cdp.pool")
        self.logger.info(f"CDP连接池初始化: {len(cdp_urls)}个URL")

    @asynccontextmanager
    async def acquire(self) -> str:
        """获取一个可用的CDP URL"""
        cdp_url = await self.available_urls.get()
        
        async with self._lock:
            self.in_use_urls[cdp_url] = True
        
        try:
            self.logger.debug(f"获取CDP URL: {cdp_url}")
            yield cdp_url
        finally:
            # 释放URL回池中
            async with self._lock:
                self.in_use_urls[cdp_url] = False
            await self.available_urls.put(cdp_url)
            self.logger.debug(f"释放CDP URL: {cdp_url}")

    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        available_count = self.available_urls.qsize()
        in_use_count = len([v for v in self.in_use_urls.values() if v])
        
        return {
            "total_urls": len(self.cdp_urls),
            "available": available_count,
            "in_use": in_use_count,
            "urls": list(self.cdp_urls)
        }
