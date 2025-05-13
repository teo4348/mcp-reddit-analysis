#!/usr/bin/env python3
"""
Reddit Analysis MCP 서버 실행 스크립트
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from app.main import start

if __name__ == "__main__":
    try:
        logging.info("Reddit Analysis MCP 서버를 시작합니다.")
        start()
    except KeyboardInterrupt:
        logging.info("사용자에 의해 서버가 중지되었습니다.")
    except Exception as e:
        logging.error(f"서버 실행 중 오류 발생: {e}", exc_info=True) 