import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict


async def crawl_naver_news(keywords: List[str], days: int = 7) -> List[Dict]:
    articles = []
    cutoff = datetime.now() - timedelta(days=days)

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for keyword in keywords[:3]:  # 키워드 3개까지
            url = f"https://news.naver.com/main/search/result.naver?query={keyword}&start=1&sort=0&field=0&is_sug_officialComp=undefined&queryX=undefined&where=news&ie=utf8&sm=tab_pge&photo=0&video=0&journalist=&office_type=0&office_section_code=0&mnid="
            try:
                rss_url = f"https://news.naver.com/main/main.nhn?mode=LSLS&mid=shm"
                # Naver 뉴스 검색 RSS 사용
                rss_url = f"https://news.naver.com/main/mainNews.nhn?mode=LSLS&mid=shm"
                # 직접 검색 결과 파싱
                resp = await client.get(
                    f"https://search.naver.com/search.naver?where=news&query={keyword}&sort=1",
                    headers={"User-Agent": "Mozilla/5.0 (compatible; CafeAIBot/1.0)"}
                )
                soup = BeautifulSoup(resp.text, "lxml")
                for item in soup.select(".news_area")[:5]:
                    title_el = item.select_one(".news_tit")
                    desc_el = item.select_one(".news_dsc")
                    if title_el:
                        articles.append({
                            "title": title_el.get_text(strip=True),
                            "body": desc_el.get_text(strip=True) if desc_el else "",
                            "url": title_el.get("href", ""),
                            "source": "naver_news",
                            "keyword": keyword,
                        })
            except Exception:
                pass

    return articles[:15]  # 최대 15개


async def crawl_daum_news(keywords: List[str]) -> List[Dict]:
    articles = []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for keyword in keywords[:3]:
            try:
                resp = await client.get(
                    f"https://search.daum.net/search?w=news&q={keyword}&sort=recency",
                    headers={"User-Agent": "Mozilla/5.0 (compatible; CafeAIBot/1.0)"}
                )
                soup = BeautifulSoup(resp.text, "lxml")
                for item in soup.select(".c-list-basic .item-title")[:5]:
                    link = item.select_one("a")
                    if link:
                        articles.append({
                            "title": link.get_text(strip=True),
                            "body": "",
                            "url": link.get("href", ""),
                            "source": "daum_news",
                            "keyword": keyword,
                        })
            except Exception:
                pass

    return articles[:10]


async def gather_context_for_quiz(keywords: List[str]) -> str:
    naver = await crawl_naver_news(keywords)
    daum = await crawl_daum_news(keywords)
    all_articles = naver + daum

    if not all_articles:
        return f"키워드 '{', '.join(keywords)}'에 대한 최신 뉴스를 찾을 수 없습니다."

    lines = []
    seen_titles = set()
    for a in all_articles:
        title = a["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        body = a["body"][:300] if a["body"] else ""
        lines.append(f"[{a['source']}] {title}\n{body}\n출처: {a['url']}")

    return "\n\n".join(lines[:12])  # 최대 12개 기사, ~8000 토큰 이내
