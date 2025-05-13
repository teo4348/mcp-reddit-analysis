# Reddit Analysis MCP 서버

이 프로젝트는 Reddit 분석을 위한 Model Context Protocol(MCP) 서버입니다. FastMCP를 사용하여 Reddit 데이터에 접근하고 분석하는 기능을 제공합니다.

## 기능

이 MCP 서버는 다음과 같은 주요 기능을 제공합니다:

1. **Reddit 검색 (search_reddit)**
   - 키워드를 기반으로 서브레딧이나 포스트를 검색
   - 특정 서브레딧 내에서 검색 가능
   - 시간 필터 적용 가능 (hour, day, week, month, year, all)

2. **Reddit 포스트 분석 (analyze_reddit_post)**
   - 특정 포스트 URL을 통해 포스트 및 댓글 분석
   - 감정 분석 (긍정/부정/중립)
   - 키워드 추출 및 주제 분석
   - 댓글 소팅 및 필터링

3. **Reddit 트렌드 분석 (analyze_reddit_trends)**
   - 특정 서브레딧 또는 r/all의 인기 트렌드 분석
   - 기간별 인기 키워드 및 토픽 추출
   - 서브레딧 활성도 평가
   - 감정 분석

## 설치 및 설정

### 요구 사항

- Python 3.10 이상
- Reddit API 계정 (client ID 및 client secret)

### 설치

```bash
# 저장소 복제
git clone https://github.com/yourusername/mcp-reddit-analysis.git
cd mcp-reddit-analysis

# 의존성 패키지 설치
pip install -r requirements.txt

# NLTK 데이터 다운로드 (이미 코드에서 자동으로 다운로드되지만, 수동으로도 가능)
python -m nltk.downloader punkt stopwords wordnet
```

### 환경 설정

`.env` 파일을 생성하고 다음 환경 변수 설정:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=python:mcp-reddit-analysis:v1.0 (by /u/your_username)
```

## 사용 방법

### 서버 실행

```bash
python run.py
```

### Claude Desktop 연결

Claude Desktop의 설정 파일에 다음과 같이 MCP 서버를 등록합니다:

#### macOS

`~/Library/Application Support/Claude/claude_desktop_config.json` 파일 편집:

```json
{
  "mcpServers": {
    "reddit-analysis": {
      "command": "python",
      "args": ["/path/to/your/mcp-reddit-analysis/run.py"]
    }
  }
}
```

#### Windows

`%APPDATA%/Claude/claude_desktop_config.json` 파일 편집:

```json
{
  "mcpServers": {
    "reddit-analysis": {
      "command": "python",
      "args": ["C:\\path\\to\\your\\mcp-reddit-analysis\\run.py"]
    }
  }
}
```

### API 요청 예시

Claude Desktop에서 다음과 같은 요청을 할 수 있습니다:

- "레딧에서 'artificial intelligence' 키워드로 검색해줘"
- "https://www.reddit.com/r/MachineLearning/comments/example URL의 포스트를 분석해줘"
- "r/technology와 r/science 서브레딧의 주간 트렌드를 분석해줘"

## 프로젝트 구조

```
mcp-reddit-analysis/
│
├── app/                      # 주요 애플리케이션 코드
│   ├── __init__.py           # 패키지 초기화
│   ├── config.py             # 설정 및 환경 변수
│   ├── main.py               # MCP 서버 초기화 및 실행
│   └── tools.py              # Reddit 분석 도구 구현
│
├── util/                     # 유틸리티 모듈 (향후 확장용)
│
├── .env                      # 환경 변수 (git에 포함되지 않음)
├── .env.example              # 환경 변수 예제
├── requirements.txt          # 의존성 패키지
├── README.md                 # 프로젝트 문서
└── run.py                    # 메인 실행 스크립트
```

## 라이센스

MIT License

## 기여

버그 리포트, 기능 요청, Pull Request 등 모든 기여를 환영합니다. 