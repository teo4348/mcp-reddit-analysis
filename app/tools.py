"""
Reddit Analysis MCP 서버의 도구 모듈

이 모듈은 Reddit 데이터를 분석하고 처리하는 MCP 도구를 제공합니다.
검색, 포스트 분석, 트렌드 분석 등의 기능을 구현합니다.
"""

import logging
import re
from datetime import datetime
import time
from collections import Counter, defaultdict
import praw
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import requests
from bs4 import BeautifulSoup

from .config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

logger = logging.getLogger(__name__)

# NLTK 리소스 초기화
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# NLTK 초기화
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

def register_tools(mcp):
    """MCP 서버에 Reddit 분석 도구를 등록합니다."""
    
    @mcp.tool()
    def fetch_webpage(url: str, extract_text: bool = True, user_agent: str = None) -> dict:
        """웹 페이지 내용을 직접 가져옵니다
        
        Args:
            url: 가져올 웹 페이지의 URL (예: https://www.reddit.com/r/python)
            extract_text: HTML에서 텍스트만 추출할지 여부 (기본값: True)
            user_agent: 요청에 사용할 User-Agent 문자열 (기본값: Reddit API user agent)
        
        Returns:
            웹 페이지의 내용 또는, 실패한 경우 오류 정보를 반환합니다
        """
        try:
            # User-Agent 설정
            headers = {
                'User-Agent': user_agent or REDDIT_USER_AGENT
            }
            
            # 웹 페이지 가져오기
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # HTTP 오류 체크
            
            # 응답 콘텐츠 처리
            if extract_text:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 스크립트와 스타일 요소 제거
                for script in soup(["script", "style"]):
                    script.extract()
                
                # 텍스트 추출
                text = soup.get_text(separator='\n')
                
                # 공백 정리
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Reddit 특화 정보 추출 (제목, 포스트 내용, 댓글 등)
                title = soup.find('title')
                title_text = title.get_text() if title else "제목을 찾을 수 없습니다"
                
                # 포스트 내용 추출 시도 (Reddit의 구조에 따라 선택자가 변경될 수 있음)
                post_content = None
                post_div = soup.select_one('div[data-test-id="post-content"]')
                if post_div:
                    post_content = post_div.get_text(strip=True)
                
                return {
                    "status": "success",
                    "url": url,
                    "title": title_text,
                    "post_content": post_content,
                    "full_text": text[:5000] + ("..." if len(text) > 5000 else ""),  # 텍스트가 너무 길면 자름
                    "content_length": len(text),
                    "content_type": response.headers.get('Content-Type', ''),
                    "is_reddit_page": "reddit.com" in url
                }
            else:
                # HTML 원본 반환
                return {
                    "status": "success",
                    "url": url,
                    "html": response.text[:5000] + ("..." if len(response.text) > 5000 else ""),  # HTML이 너무 길면 자름
                    "content_length": len(response.text),
                    "content_type": response.headers.get('Content-Type', ''),
                    "is_reddit_page": "reddit.com" in url
                }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"웹 페이지 가져오기 오류: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "url": url,
                "message": f"웹 페이지 가져오기 중 오류 발생: {str(e)}"
            }
        except Exception as e:
            logger.error(f"웹 페이지 처리 중 오류: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "url": url,
                "message": f"웹 페이지 처리 중 오류 발생: {str(e)}"
            }

    @mcp.tool()
    def search_reddit(query: str, search_type: str = "post", subreddit: str = None, time_filter: str = "month", limit: int = 20) -> dict:
        """레딧에서 키워드로 서브레딧 또는 포스트를 검색합니다
        
        Args:
            query: 검색할 키워드
            search_type: 검색 유형 ('post', 'subreddit' 중 하나)
            subreddit: 특정 서브레딧 내에서 검색할 경우 서브레딧 이름 (예: 'python', 'AskReddit')
            time_filter: 검색 기간 ('hour', 'day', 'week', 'month', 'year', 'all' 중 하나)
            limit: 검색 결과 수 (기본값: 20)
        
        Returns:
            검색 결과 목록을 반환합니다
        """
        try:
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                return {
                    "status": "error",
                    "message": "레딧 API 인증 정보가 설정되어 있지 않습니다. 환경 변수에 REDDIT_CLIENT_ID와 REDDIT_CLIENT_SECRET을 설정해주세요."
                }
            
            # 유효한 검색 유형 확인
            if search_type not in ["post", "subreddit"]:
                return {
                    "status": "error",
                    "message": "유효하지 않은 검색 유형입니다. 'post' 또는 'subreddit'을 사용하세요."
                }
            
            # 유효한 시간 필터 확인
            if time_filter not in ["hour", "day", "week", "month", "year", "all"]:
                return {
                    "status": "error",
                    "message": "유효하지 않은 시간 필터입니다. 'hour', 'day', 'week', 'month', 'year', 'all' 중 하나를 사용하세요."
                }
            
            # 레딧 API 인스턴스 생성
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT
            )
            
            results = []
            
            # 서브레딧 검색
            if search_type == "subreddit":
                subreddits = reddit.subreddits.search(query, limit=limit)
                
                for sr in subreddits:
                    subreddit_data = {
                        "name": sr.display_name,
                        "title": sr.title,
                        "description": sr.public_description,
                        "subscribers": sr.subscribers,
                        "url": f"https://www.reddit.com{sr.url}",
                        "created_utc": datetime.fromtimestamp(sr.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "is_nsfw": sr.over18
                    }
                    results.append(subreddit_data)
            
            # 포스트 검색
            else:
                if subreddit:
                    # 특정 서브레딧 내에서 검색
                    sr = reddit.subreddit(subreddit)
                    posts = sr.search(query, time_filter=time_filter, limit=limit)
                else:
                    # 전체 레딧에서 검색
                    posts = reddit.subreddit("all").search(query, time_filter=time_filter, limit=limit)
                
                for post in posts:
                    post_data = {
                        "id": post.id,
                        "title": post.title,
                        "author": str(post.author) if post.author else "[deleted]",
                        "subreddit": post.subreddit.display_name,
                        "score": post.score,
                        "upvote_ratio": post.upvote_ratio,
                        "num_comments": post.num_comments,
                        "created_utc": datetime.fromtimestamp(post.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "url": f"https://www.reddit.com{post.permalink}",
                        "is_self": post.is_self,
                        "selftext_preview": post.selftext[:300] + "..." if len(post.selftext) > 300 else post.selftext,
                        "is_nsfw": post.over_18
                    }
                    results.append(post_data)
            
            return {
                "status": "success",
                "query": query,
                "search_type": search_type,
                "subreddit": subreddit,
                "time_filter": time_filter,
                "result_count": len(results),
                "results": results
            }
        
        except Exception as e:
            logger.error(f"레딧 검색 중 오류: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"레딧 검색 중 오류 발생: {str(e)}"
            }

    @mcp.tool()
    def analyze_reddit_post(post_url: str, comment_sort: str = "top", comment_limit: int = 100) -> dict:
        """레딧 포스트의 댓글을 분석하여 인사이트를 제공합니다
        
        Args:
            post_url: 레딧 포스트 URL
            comment_sort: 댓글 정렬 방식 ('top', 'best', 'new', 'controversial', 'old', 'qa' 중 하나)
            comment_limit: 분석할 댓글 수 (기본값: 100)
        
        Returns:
            포스트 정보와 댓글 분석 결과를 반환합니다
        """
        try:
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                return {
                    "status": "error",
                    "message": "레딧 API 인증 정보가 설정되어 있지 않습니다. 환경 변수에 REDDIT_CLIENT_ID와 REDDIT_CLIENT_SECRET을 설정해주세요."
                }
            
            # 유효한 정렬 방식 확인
            if comment_sort not in ["top", "best", "new", "controversial", "old", "qa"]:
                return {
                    "status": "error",
                    "message": "유효하지 않은 댓글 정렬 방식입니다. 'top', 'best', 'new', 'controversial', 'old', 'qa' 중 하나를 사용하세요."
                }
            
            # 레딧 API 인스턴스 생성
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT
            )
            
            # URL에서 포스트 ID 추출
            post_id = None
            id_match = re.search(r'/comments/([a-z0-9]+)/', post_url, re.IGNORECASE)
            if id_match:
                post_id = id_match.group(1)
            else:
                return {
                    "status": "error",
                    "message": "유효하지 않은 레딧 포스트 URL입니다."
                }
            
            # 포스트 정보 가져오기
            post = reddit.submission(id=post_id)
            
            # 포스트 기본 정보
            post_info = {
                "id": post.id,
                "title": post.title,
                "author": str(post.author) if post.author else "[deleted]",
                "subreddit": post.subreddit.display_name,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "created_utc": datetime.fromtimestamp(post.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                "selftext": post.selftext,
                "url": f"https://www.reddit.com{post.permalink}",
                "is_nsfw": post.over_18
            }
            
            # 댓글 추출 및 분석 준비
            post.comment_sort = comment_sort
            post.comments.replace_more(limit=10)  # 더보기 버튼 처리
            
            comments = []
            all_comment_text = ""
            comment_sentiments = []
            keywords = Counter()
            
            # 댓글 정보 추출 및 분석
            for comment in post.comments.list()[:comment_limit]:
                if not comment.author:
                    continue  # 삭제된 댓글 건너뛰기
                    
                comment_text = comment.body
                
                # 감정 분석
                sentiment = TextBlob(comment_text).sentiment
                sentiment_label = "positive" if sentiment.polarity > 0.1 else "negative" if sentiment.polarity < -0.1 else "neutral"
                
                # 댓글 정보 저장
                comment_data = {
                    "id": comment.id,
                    "author": str(comment.author),
                    "score": comment.score,
                    "created_utc": datetime.fromtimestamp(comment.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "text": comment_text[:300] + "..." if len(comment_text) > 300 else comment_text,
                    "sentiment": {
                        "polarity": sentiment.polarity,
                        "subjectivity": sentiment.subjectivity,
                        "label": sentiment_label
                    }
                }
                comments.append(comment_data)
                
                # 텍스트 분석을 위한 데이터 축적
                all_comment_text += " " + comment_text
                comment_sentiments.append(sentiment.polarity)
                
                # 키워드 추출
                tokens = word_tokenize(comment_text.lower())
                # 불용어 및 구두점 제거, 단어 원형화
                filtered_tokens = [lemmatizer.lemmatize(word) for word in tokens 
                                  if word not in stop_words and word not in string.punctuation
                                  and len(word) > 2]
                keywords.update(filtered_tokens)
            
            # 감정 분석 요약
            avg_sentiment = sum(comment_sentiments) / len(comment_sentiments) if comment_sentiments else 0
            sentiment_counts = {
                "positive": sum(1 for s in comment_sentiments if s > 0.1),
                "neutral": sum(1 for s in comment_sentiments if -0.1 <= s <= 0.1),
                "negative": sum(1 for s in comment_sentiments if s < -0.1)
            }
            
            # 상위 키워드 추출
            top_keywords = [{"word": word, "count": count} for word, count in keywords.most_common(20)]
            
            # 주제별 댓글 그룹화 (기본적인 구현)
            topics = defaultdict(list)
            for i, comment in enumerate(comments):
                # 상위 키워드를 활용한 토픽 할당 (단순화된 방식)
                assigned_topic = None
                comment_text = comment["text"].lower()
                
                for kw in top_keywords[:10]:  # 상위 10개 키워드만 사용
                    if kw["word"] in comment_text:
                        assigned_topic = kw["word"]
                        break
                
                if assigned_topic:
                    topics[assigned_topic].append(i)  # 댓글 인덱스 저장
            
            # 주제별 댓글 요약
            topic_summaries = []
            for topic, comment_indices in topics.items():
                if len(comment_indices) > 1:  # 최소 2개 이상의 댓글이 있는 주제만
                    topic_comments = [comments[i] for i in comment_indices]
                    avg_sentiment = sum(c["sentiment"]["polarity"] for c in topic_comments) / len(topic_comments)
                    
                    topic_summaries.append({
                        "topic": topic,
                        "comment_count": len(comment_indices),
                        "avg_sentiment": avg_sentiment,
                        "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
                        "sample_comments": [comments[i]["text"] for i in comment_indices[:3]]
                    })
            
            return {
                "status": "success",
                "post_info": post_info,
                "comment_analysis": {
                    "comment_count": len(comments),
                    "overall_sentiment": {
                        "average_polarity": avg_sentiment,
                        "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
                        "sentiment_distribution": sentiment_counts
                    },
                    "top_keywords": top_keywords,
                    "topic_analysis": topic_summaries
                },
                "comments": comments[:20]  # 상위 20개 댓글만 반환
            }
        
        except Exception as e:
            logger.error(f"레딧 포스트 분석 중 오류: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"레딧 포스트 분석 중 오류 발생: {str(e)}"
            }

    @mcp.tool()
    def analyze_reddit_trends(subreddits: list = None, time_period: str = "day", limit: int = 50) -> dict:
        """레딧의 인기 키워드 및 트렌드를 분석합니다
        
        Args:
            subreddits: 분석할 서브레딧 목록 (예: ['worldnews', 'technology']). 비워두면 r/all 사용
            time_period: 분석 기간 ('hour', 'day', 'week', 'month', 'year' 중 하나)
            limit: 분석할 포스트 수 (기본값: 50)
        
        Returns:
            인기 키워드, 감정 분석, 트렌드 정보를 반환합니다
        """
        try:
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                return {
                    "status": "error",
                    "message": "레딧 API 인증 정보가 설정되어 있지 않습니다. 환경 변수에 REDDIT_CLIENT_ID와 REDDIT_CLIENT_SECRET을 설정해주세요."
                }
            
            # 유효한 시간 필터 확인
            if time_period not in ["hour", "day", "week", "month", "year"]:
                return {
                    "status": "error",
                    "message": "유효하지 않은 시간 기간입니다. 'hour', 'day', 'week', 'month', 'year' 중 하나를 사용하세요."
                }
            
            # 레딧 API 인스턴스 생성
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT
            )
            
            # 분석할 서브레딧 결정
            if not subreddits:
                subreddits = ["all"]  # 기본값으로 r/all 사용
            
            all_posts = []
            subreddit_stats = {}
            
            # 각 서브레딧의 인기 포스트 수집
            for subreddit_name in subreddits:
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # 서브레딧 통계 초기화
                    subreddit_stats[subreddit_name] = {
                        "post_count": 0,
                        "total_score": 0,
                        "total_comments": 0,
                        "keywords": Counter(),
                        "sentiments": []
                    }
                    
                    # 인기 포스트 가져오기
                    for post in getattr(subreddit, f"top")(time_filter=time_period, limit=limit):
                        # 포스트 정보 저장
                        post_data = {
                            "id": post.id,
                            "title": post.title,
                            "subreddit": post.subreddit.display_name,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "created_utc": datetime.fromtimestamp(post.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                            "url": f"https://www.reddit.com{post.permalink}"
                        }
                        all_posts.append(post_data)
                        
                        # 서브레딧 통계 업데이트
                        subreddit_stats[subreddit_name]["post_count"] += 1
                        subreddit_stats[subreddit_name]["total_score"] += post.score
                        subreddit_stats[subreddit_name]["total_comments"] += post.num_comments
                        
                        # 텍스트 분석
                        combined_text = post.title
                        if post.selftext:
                            combined_text += " " + post.selftext
                            
                        # 감정 분석
                        sentiment = TextBlob(combined_text).sentiment.polarity
                        subreddit_stats[subreddit_name]["sentiments"].append(sentiment)
                        
                        # 키워드 추출
                        tokens = word_tokenize(combined_text.lower())
                        # 불용어 및 구두점 제거, 단어 원형화
                        filtered_tokens = [lemmatizer.lemmatize(word) for word in tokens 
                                          if word not in stop_words and word not in string.punctuation
                                          and len(word) > 2]
                        subreddit_stats[subreddit_name]["keywords"].update(filtered_tokens)
                        
                        # API 호출 간격 조정 (레딧 API 제한 준수)
                        time.sleep(0.1)
                    
                    # 서브레딧 감정 평균 계산
                    sentiments = subreddit_stats[subreddit_name]["sentiments"]
                    subreddit_stats[subreddit_name]["avg_sentiment"] = sum(sentiments) / len(sentiments) if sentiments else 0
                    
                    # 서브레딧 키워드 요약
                    subreddit_stats[subreddit_name]["top_keywords"] = [
                        {"word": word, "count": count} 
                        for word, count in subreddit_stats[subreddit_name]["keywords"].most_common(10)
                    ]
                    
                except Exception as e:
                    subreddit_stats[subreddit_name] = {
                        "error": f"서브레딧 분석 중 오류 발생: {str(e)}"
                    }
            
            # 전체 트렌드 분석
            all_keywords = Counter()
            all_sentiments = []
            
            for sr_name, stats in subreddit_stats.items():
                if "keywords" in stats:
                    all_keywords.update(stats["keywords"])
                if "sentiments" in stats:
                    all_sentiments.extend(stats["sentiments"])
            
            # 전체 인기 키워드
            trending_keywords = [{"word": word, "count": count} for word, count in all_keywords.most_common(20)]
            
            # 전체 감정 분석
            avg_sentiment = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0
            sentiment_label = "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral"
            
            # 서브레딧 활성도 평가
            subreddit_activity = []
            for sr_name, stats in subreddit_stats.items():
                if "total_score" in stats:
                    activity_score = (stats["total_score"] / 100) + stats["total_comments"]
                    subreddit_activity.append({
                        "subreddit": sr_name,
                        "activity_score": activity_score,
                        "post_count": stats["post_count"],
                        "total_score": stats["total_score"],
                        "total_comments": stats["total_comments"],
                        "avg_sentiment": stats.get("avg_sentiment", 0)
                    })
            
            # 활성도 기준으로 정렬
            subreddit_activity.sort(key=lambda x: x["activity_score"], reverse=True)
            
            # 주제별 분류 (단순화된 구현)
            topics = defaultdict(list)
            for keyword, _ in trending_keywords[:10]:  # 상위 10개 키워드를 주제로 사용
                for post in all_posts:
                    if keyword in post["title"].lower():
                        topics[keyword].append(post["id"])
            
            # 주제별 요약
            topic_summaries = []
            for topic, post_ids in topics.items():
                if len(post_ids) > 1:  # 최소 2개 이상의 포스트가 있는 주제만
                    relevant_posts = [p for p in all_posts if p["id"] in post_ids]
                    avg_score = sum(p["score"] for p in relevant_posts) / len(relevant_posts)
                    
                    topic_summaries.append({
                        "topic": topic,
                        "post_count": len(post_ids),
                        "avg_score": avg_score,
                        "sample_posts": [p["title"] for p in relevant_posts[:3]]
                    })
            
            return {
                "status": "success",
                "analysis_period": time_period,
                "subreddits_analyzed": subreddits,
                "trending_keywords": trending_keywords,
                "overall_sentiment": {
                    "average_polarity": avg_sentiment,
                    "sentiment_label": sentiment_label
                },
                "subreddit_activity": subreddit_activity,
                "topic_analysis": topic_summaries,
                "trending_posts": sorted(all_posts, key=lambda x: x["score"], reverse=True)[:10]  # 상위 10개 포스트
            }
        
        except Exception as e:
            logger.error(f"레딧 트렌드 분석 중 오류: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"레딧 트렌드 분석 중 오류 발생: {str(e)}"
            }
    
    logger.info("모든 Reddit 분석 도구가 등록되었습니다.") 