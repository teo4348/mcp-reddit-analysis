"""
Reddit Analysis MCP 서버의 설정 모듈

이 모듈은 환경 변수를 로드하고 서버의 설정 값을 관리합니다.
Reddit API 인증 정보와 기타 설정을 초기화합니다.
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 환경 변수
REDDIT_CLIENT_ID = None
REDDIT_CLIENT_SECRET = None
REDDIT_USER_AGENT = None

def init_environment():
    """환경 변수를 초기화합니다."""
    global REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    
    # .env 파일 로드
    load_dotenv()
    
    # Reddit API 설정
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "python:mcp-reddit-analysis:v1.0 (by /u/your_username)")
    
    # 필수 환경 변수 확인
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning("Reddit API 인증 정보가 설정되지 않았습니다. Reddit 관련 기능은 작동하지 않을 수 있습니다.")
    else:
        logger.info("Reddit API 인증 정보가 성공적으로 로드되었습니다.")
        
    return {
        "REDDIT_CLIENT_ID": REDDIT_CLIENT_ID,
        "REDDIT_CLIENT_SECRET": REDDIT_CLIENT_SECRET,
        "REDDIT_USER_AGENT": REDDIT_USER_AGENT
    } 