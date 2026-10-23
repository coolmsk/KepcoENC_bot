import os
import json
import requests
import google.generativeai as genai

# 1. 환경 변수에서 API 키 불러오기
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeAIModel('gemini-1.5-flash')

# 이전 분석 기사 중복 방지 파일 경로
PROCESSED_FILE = "processed_articles.json"

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_processed(processed_set):
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_set), f, ensure_ascii=False)

def get_naver_news(query="한국전력기술"):
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=date"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def analyze_sentiment(title, description):
    prompt = f"""
    당신은 기업 리스크 분석 전문가입니다.
    아래 뉴스 기사의 제목과 요약 내용을 읽고, '한국전력기술' 입장에서 부정적인 내용(비리, 징계, 보안, 사고, 사망, 산재, 유출, 실적 악화, 이해충돌 등 리스크 등)인지 판단하세요.
    
    [제목]: {title}
    [내용]: {description}
    
    응답은 반드시 JSON 포맷으로 작성하세요:
    {{"is_negative": true 또는 false, "reason": "부정적인 이유 한 줄 요약"}}
    """
    try:
        response = model.generate_content(prompt)
        # JSON 텍스트 정제
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result.get("is_negative", False), result.get("reason", "")
    except Exception as e:
        print(f"Gemini 분석 오류: {e}")
        return False, ""

def send_telegram(title, link, reason):
    msg = f"🚨 **[한국전력기술 리스크 뉴스 알림]**\n\n📌 **제목**: {title}\n⚠️ **사유**: {reason}\n\n🔗 [기사 읽기]({link})"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def main():
    processed = load_processed()
    news_list = get_naver_news()

    for news in news_list:
        link = news.get("originallink") or news.get("link")
        
        # 이미 처리한 기사는 스킵
        if link in processed:
            continue
        
        title = news.get("title").replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        description = news.get("description").replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        
        is_negative, reason = analyze_sentiment(title, description)
        
        if is_negative:
            send_telegram(title, link, reason)
            print(f"[발송 완료] {title}")
        
        # 처리 목록 추가
        processed.add(link)

    save_processed(processed)

if __name__ == "__main__":
    main()
