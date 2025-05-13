"""
Reddit Analysis MCP 서버의 메인 모듈

이 모듈은 MCP 서버를 초기화하고 시작합니다.
Reddit API 관련 도구를 등록하고 서버를 실행합니다.
"""

import logging
import sys
from mcp.server.fastmcp import FastMCP

from .tools import register_tools
from .config import init_environment

logger = logging.getLogger(__name__)

def start():
    """Reddit Analysis MCP 서버를 초기화하고 시작합니다."""
    try:
        logger.info("Reddit Analysis MCP 서버를 초기화합니다.")
        
        # 환경 변수 초기화
        init_environment()
        
        # MCP 서버 인스턴스 생성
        mcp = FastMCP("reddit-analysis")
        
        # 도구 등록
        register_tools(mcp)
        logger.info("Reddit 분석 도구가 등록되었습니다.")
        
        # 서버 시작
        logger.info("MCP 서버를 시작합니다.")
        mcp.run()
    except Exception as e:
        logger.error(f"MCP 서버 초기화 중 오류 발생: {e}", exc_info=True)
        sys.exit(1) 