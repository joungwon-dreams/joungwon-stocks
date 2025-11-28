"""
Gemini AI 투자 포인트 분석 테스트

FnGuide 데이터를 사용하여 Gemini AI로 투자 포인트를 생성합니다.
"""
import asyncio
import asyncpg
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 환경변수 로드
load_dotenv()

# DB 설정
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_investment_db',
    'user': 'wonny'
}

KEPCO_CODE = '015760'
KEPCO_NAME = '한국전력'


async def fetch_fnguide_data(stock_code: str) -> dict:
    """FnGuide 데이터 조회"""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        query = """
        SELECT data_content
        FROM collected_data
        WHERE ticker = $1 AND site_id = 53 AND data_type = 'fnguide_analysis'
        ORDER BY collected_at DESC
        LIMIT 1
        """
        row = await conn.fetchrow(query, stock_code)

        if row and row['data_content']:
            data = row['data_content']
            # JSONB가 dict가 아닌 경우 파싱
            if isinstance(data, str):
                data = json.loads(data)
            # data 키 안에 실제 데이터가 있는 경우
            if 'data' in data:
                return data['data']
            return data
        return {}
    finally:
        await conn.close()


def analyze_with_gemini(fnguide_data: dict) -> dict:
    """Gemini AI를 사용한 투자 포인트 분석"""

    # Gemini API 설정
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 분석할 데이터 추출
    financial_summary = fnguide_data.get('financial_summary', {})
    valuation_metrics = fnguide_data.get('valuation_metrics', {})
    analyst_consensus = fnguide_data.get('analyst_consensus', {})

    # 프롬프트 구성
    prompt = f"""
당신은 전문 주식 애널리스트입니다. 다음 재무 데이터를 분석하여 투자 포인트를 도출해주세요.

## 재무 데이터

### 재무제표 요약
- 연도: {financial_summary.get('years', [])}
- 매출액 (억원): {financial_summary.get('revenue', [])}
- 영업이익 (억원): {financial_summary.get('operating_profit', [])}
- 순이익 (억원): {financial_summary.get('net_profit', [])}
- ROE (%): {financial_summary.get('roe', [])}

### 밸류에이션
- PER: {valuation_metrics.get('per', 'N/A')}배
- PBR: {valuation_metrics.get('pbr', 'N/A')}배
- 배당수익률: {valuation_metrics.get('dividend_yield', 'N/A')}%

### 애널리스트 컨센서스
- 목표주가: {analyst_consensus.get('target_price', 'N/A')}원
- 투자의견 분포: {analyst_consensus.get('opinion_distribution', {})}
- 커버리지: {analyst_consensus.get('analyst_count', 'N/A')}명

## 요청사항

다음 형식으로 투자 포인트를 분석해주세요:

### 1. 재무 건전성
- 매출 성장성, 수익성 개선 여부를 분석
- 각 포인트는 ✅ (강점), ✓ (보통), ⚠️ (주의) 로 표시

### 2. 밸류에이션
- PER, PBR, 배당수익률 기반 저평가/고평가 판단
- 동일 기호 사용

### 3. 애널리스트 의견
- 목표주가 상승여력, 투자의견 분포 해석
- 동일 기호 사용

### 4. 종합 투자 의견
- 위 분석을 종합한 1-2문장의 투자 의견

각 카테고리별로 구체적인 수치를 언급하며 bullet point로 작성해주세요.
"""

    # Gemini API 호출
    response = model.generate_content(prompt)

    # 결과 파싱
    result = {
        'analysis': response.text,
        'raw_prompt': prompt
    }

    return result


async def main():
    print(f"{'='*60}")
    print(f"Gemini AI 투자 포인트 분석 테스트")
    print(f"종목: {KEPCO_NAME} ({KEPCO_CODE})")
    print(f"{'='*60}\n")

    # 1. FnGuide 데이터 조회
    print("1. FnGuide 데이터 조회 중...")
    fnguide_data = await fetch_fnguide_data(KEPCO_CODE)

    if not fnguide_data:
        print("❌ FnGuide 데이터가 없습니다. 먼저 데이터 수집을 실행하세요.")
        return

    print("✅ FnGuide 데이터 조회 완료")
    print(f"   - 재무제표: {len(fnguide_data.get('financial_summary', {}).get('years', []))}개년")
    print(f"   - 밸류에이션: PER={fnguide_data.get('valuation_metrics', {}).get('per', 'N/A')}")
    print(f"   - 컨센서스: {fnguide_data.get('analyst_consensus', {}).get('analyst_count', 'N/A')}명 커버리지\n")

    # 2. Gemini AI 분석
    print("2. Gemini AI 분석 중...")
    try:
        analysis_result = analyze_with_gemini(fnguide_data)
        print("✅ Gemini AI 분석 완료\n")

        # 3. 결과 출력
        print(f"{'='*60}")
        print("투자 포인트 분석 결과")
        print(f"{'='*60}\n")
        print(analysis_result['analysis'])
        print(f"\n{'='*60}")

        # 4. 결과 저장
        output_path = '/tmp/gemini_investment_analysis.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 분석 결과 저장: {output_path}")

    except Exception as e:
        print(f"❌ Gemini API 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
