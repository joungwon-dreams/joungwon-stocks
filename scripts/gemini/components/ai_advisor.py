
import google.generativeai as genai
import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class AIInvestmentAdvisor:
    def __init__(self):
        # Assuming GEMINI_API_KEY is in env or we rely on default config if set elsewhere
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def get_investment_advice(self, portfolio: List[Dict], market_status: Dict) -> List[Dict]:
        """
        Analyze portfolio and market status to generate buy/sell recommendations.
        Output: List of dicts {action, stock, price, qty, reason}
        """
        try:
            # 1. Construct Prompt
            prompt = self._create_prompt(portfolio, market_status)
            
            # 2. Call Gemini
            response = self.model.generate_content(prompt)
            text = response.text
            
            # 3. Parse JSON
            # Clean up markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            advice_list = json.loads(text)
            return advice_list
            
        except Exception as e:
            logger.error(f"AI Advisor Error: {e}")
            return []

    def _create_prompt(self, portfolio, market):
        # Simplify portfolio for prompt
        port_summary = []
        for p in portfolio:
            port_summary.append({
                'name': p['name'],
                'avg_price': int(p['avg_price']),
                'current_price': int(p['current_price']),
                'return_rate': round(p['return_rate'], 2),
                'amount': int(p['eval_amt'])
            })
            
        prompt = f"""
        You are a professional AI Fund Manager. Analyze the following portfolio and market status.
        
        [Market Status]
        KOSPI: {market.get('KOSPI', {}).get('price', 0)} ({market.get('KOSPI', {}).get('rate', 0)}%)
        KOSDAQ: {market.get('KOSDAQ', {}).get('price', 0)} ({market.get('KOSDAQ', {}).get('rate', 0)}%)
        
        [Current Portfolio]
        {json.dumps(port_summary, indent=2, ensure_ascii=False)}
        
        [Instructions]
        Based on the portfolio performance and typical market logic (buy low, sell high, cut losses, ride winners), 
        recommend 3 to 5 specific actions (BUY, SELL, or HOLD).
        - If a stock has dropped significantly (> -5%) but has good fundamentals, consider BUY (averaging down).
        - If a stock has risen significantly (> +10%), consider SELL (taking profit).
        - Be concise.
        
        Return ONLY a valid JSON array. Format:
        [
            {{
                "action": "BUY" or "SELL" or "HOLD",
                "stock": "Stock Name",
                "qty": 10,
                "reason": "Short reason in Korean (max 15 words)"
            }}
        ]
        """
        return prompt
