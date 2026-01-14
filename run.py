#!/usr/bin/env python
"""
启动脚本 - 启动 FastAPI 服务
"""

import uvicorn
from app.config import get_settings


def main():
    """启动服务"""
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

