"""
Gemini AI Client
Handles interaction with Google's Gemini API for text generation and analysis.
"""
import logging
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google Gemini API"""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. AI features will be disabled.")
            self.model = None
        else:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-3-pro')
                logger.info("Gemini AI client initialized (gemini-3-pro)")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI client: {e}")
                self.model = None

    async def generate_content(self, prompt: str) -> Optional[str]:
        """Generate content from a text prompt"""
        if not self.model:
            return None

        try:
            # Gemini API call (synchronous, but fast enough for now, or wrap in executor if needed)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None

    async def analyze_stock(self, stock_name: str, news_data: List[Dict[str, Any]], realtime_data: Dict[str, Any], history_data: List[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Analyze stock based on news, comprehensive real-time data, and historical trends.
        Returns a dictionary with analysis sections.
        """
        if not self.model:
            return {
                "summary": "AI 분석을 사용할 수 없습니다 (API Key 미설정).",
                "sentiment": "N/A",
                "recommendation": "N/A"
            }

        # Extract Real-time Data
        daum = realtime_data.get('daum', {})
        naver = realtime_data.get('naver', {})
        
        quotes = daum.get('quotes', {})
        financials = daum.get('financials', {})
        investors = daum.get('investor_trends', [])
        consensus = naver.get('consensus', {})
        peers = naver.get('peers', [])

        # Analyze History (if available)
        history_context = "과거 데이터 없음"
        if history_data:
            try:
                # Simple metrics from history
                closes = [d['close'] for d in history_data]
                highs = [d['high'] for d in history_data]
                lows = [d['low'] for d in history_data]
                volumes = [d['volume'] for d in history_data]
                
                year_high = max(highs)
                year_low = min(lows)
                avg_vol = sum(volumes) / len(volumes)
                current_close = closes[-1]
                start_close = closes[0]
                year_return = ((current_close - start_close) / start_close) * 100
                
                history_context = f"""
                [지난 1년 주가 흐름]
                52주 최고가: {year_high:,}원
                52주 최저가: {year_low:,}원
                1년 수익률: {year_return:.2f}%
                평균 거래량: {avg_vol:,.0f}주
                추세: {'상승' if year_return > 0 else '하락'}세
                """
            except Exception as e:
                logger.error(f"Error analyzing history: {e}")

        # Construct context from news
        news_context = ""
        if news_data:
            for item in news_data[:5]:
                title = item.get('title', 'No Title')
                content = item.get('content', '')[:200]
                date = item.get('collected_at', '')
                news_context += f"- [{date}] {title}: {content}...\n"
        else:
            news_context = "최근 관련 뉴스가 없습니다."

        # Construct context from Real-time Data
        market_context = f"""
        [시세 정보]
        현재가: {quotes.get('tradePrice', 'N/A')}원
        등락률: {quotes.get('changeRate', 'N/A')}%
        거래량: {quotes.get('accTradeVolume', 'N/A')}
        외국인소진율: {quotes.get('foreignRatio', 'N/A')}%
        
        [투자자 동향 (최근 5일)]
        {investors}
        
        [재무 지표]
        PER: {financials.get('per', 'N/A')}
        PBR: {financials.get('pbr', 'N/A')}
        ROE: {financials.get('roe', 'N/A')}
        
        [컨센서스]
        목표주가: {consensus.get('target_price', 'N/A')}
        투자의견: {consensus.get('opinion', 'N/A')}
        
        [동종 업종]
        {', '.join(peers)}
        """

        prompt = f"""
        당신은 전문 주식 애널리스트입니다. 다음 데이터를 바탕으로 '{stock_name}' 종목에 대한 심층 투자 분석 리포트를 작성해주세요.

        [시장 데이터]
        {market_context}
        
        [기술적 분석 데이터]
        {history_context}

        [최근 뉴스]
        {news_context}

        다음 3가지 항목으로 나누어 답변해주세요:
        1. 종합 분석 (300자 내외): 
           - 펀더멘털(재무), 수급(외국인/기관), 모멘텀(뉴스)을 종합적으로 분석
           - 동종 업종 대비 경쟁력 언급
        2. 시장 감성 (긍정/중립/부정): 
           - 뉴스와 시장 분위기에 따른 감성 판단
        3. 투자 제안 (매수/매도/관망): 
           - 컨센서스와 현재가를 비교하여 구체적인 진입/청산 전략 제안
           - 리스크 요인 포함

        답변 형식:
        ---
        종합 분석: [내용]
        시장 감성: [내용]
        투자 제안: [내용]
        ---
        """

        response_text = await self.generate_content(prompt)
        
        if not response_text:
             return {
                "summary": "AI 분석 생성 실패.",
                "sentiment": "N/A",
                "recommendation": "N/A"
            }

        # Simple parsing
        analysis = {
            "summary": "",
            "sentiment": "",
            "recommendation": ""
        }
        
        try:
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("종합 분석:"):
                    current_section = "summary"
                    analysis["summary"] += line.replace("종합 분석:", "").strip()
                elif line.startswith("시장 감성:"):
                    current_section = "sentiment"
                    analysis["sentiment"] += line.replace("시장 감성:", "").strip()
                elif line.startswith("투자 제안:"):
                    current_section = "recommendation"
                    analysis["recommendation"] += line.replace("투자 제안:", "").strip()
                elif current_section and line and not line.startswith("---"):
                    analysis[current_section] += " " + line
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            analysis["summary"] = response_text

        return analysis
