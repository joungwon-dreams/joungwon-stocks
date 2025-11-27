"""
Phase 2B: Gemini AI 배치 분석
50개 종목을 5개씩 묶어서 AI 분석

목표: ~2.5분 내 실행
방법: 5개 종목 배치 → 10회 API 호출
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
import os

import google.generativeai as genai

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.phase2.batch_collector import CollectedData

logger = logging.getLogger(__name__)


class GeminiBatchAnalyzer:
    """
    Gemini AI 배치 분석기

    전략:
    1. 5개 종목씩 묶어서 1회 호출 (토큰 효율화)
    2. 구조화된 JSON 응답 요청
    3. Rate Limit: 6 calls/min (10초 간격)
    """

    def __init__(self, config=None):
        self.config = config or settings.phase2b

        # Gemini API 설정
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
                logger.info("Gemini 모델 초기화: gemini-2.0-flash-lite")
            except Exception as e:
                logger.error(f"Gemini 초기화 실패: {e}")
        else:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다")

    async def analyze_batch(
        self,
        candidates: List[Dict[str, Any]],
        collected_data: Dict[str, CollectedData]
    ) -> List[Dict[str, Any]]:
        """
        50개 종목 배치 AI 분석

        Args:
            candidates: Phase 1B 결과 (정량 데이터)
            collected_data: Phase 2A 결과 (뉴스/리포트/컨센서스)

        Returns:
            AI 분석 결과가 추가된 종목 리스트
        """
        if not candidates:
            return []

        if not self.model:
            logger.warning("Gemini 모델이 없어 기본 등급 할당")
            return self._assign_default_grades(candidates)

        start_time = datetime.now()
        logger.info(f"Phase 2B 시작: {len(candidates)}개 종목 AI 분석")

        # 5개씩 배치 분할
        batches = [
            candidates[i:i+self.config.batch_size]
            for i in range(0, len(candidates), self.config.batch_size)
        ]

        results = []

        for batch_idx, batch in enumerate(batches, 1):
            logger.info(f"배치 {batch_idx}/{len(batches)} 분석 중...")

            batch_results = await self._analyze_single_batch(batch, collected_data)
            results.extend(batch_results)

            # Rate limit 대기 (마지막 배치 제외)
            if batch_idx < len(batches):
                await asyncio.sleep(self.config.rate_delay_seconds)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Phase 2B 완료: {len(results)}개 종목 분석 ({elapsed:.1f}초)")

        return results

    async def _analyze_single_batch(
        self,
        batch: List[Dict],
        collected_data: Dict[str, CollectedData]
    ) -> List[Dict]:
        """5개 종목 단일 배치 분석"""
        # 프롬프트 생성
        prompt = self._build_batch_prompt(batch, collected_data)

        try:
            # Gemini API 호출 (동기 함수를 스레드에서 실행)
            response = await asyncio.to_thread(
                self._call_gemini_api,
                prompt
            )

            # 응답 파싱
            return self._parse_batch_response(response, batch)

        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            # 실패 시 기본 등급 할당
            return self._assign_default_grades(batch)

    def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출"""
        response = self.model.generate_content(prompt)
        return response.text

    def _build_batch_prompt(
        self,
        batch: List[Dict],
        collected_data: Dict[str, CollectedData]
    ) -> str:
        """배치용 프롬프트 생성"""
        stocks_info = []

        for i, stock in enumerate(batch, 1):
            code = stock['stock_code']
            collected = collected_data.get(code, CollectedData(stock_code=code))

            # 뉴스 포맷
            news_text = ""
            if collected.news:
                news_items = [f"  - {n.get('title', '')}" for n in collected.news[:5]]
                news_text = "\n".join(news_items)
            else:
                news_text = "  (최근 뉴스 없음)"

            # 컨센서스 포맷
            consensus = collected.consensus
            consensus_text = ""
            if consensus:
                avg_target = consensus.get('avg_target_price', 0)
                buy = consensus.get('buy', 0)
                hold = consensus.get('hold', 0)
                sell = consensus.get('sell', 0)
                if avg_target or buy or hold or sell:
                    consensus_text = f"평균 목표가: {avg_target:,}원, 매수:{buy} 중립:{hold} 매도:{sell}"
                else:
                    consensus_text = "(컨센서스 없음)"
            else:
                consensus_text = "(컨센서스 없음)"

            # 정책 키워드
            policy_text = ", ".join(collected.policy_keywords) if collected.policy_keywords else "(없음)"

            # 모멘텀 지표 포맷
            vol_surge = stock.get('volume_surge_ratio', 0)
            trading_val = stock.get('trading_value', 0)
            ma_aligned = "✅ 정배열" if stock.get('ma_alignment', False) else "❌ 역배열"
            high_52w = stock.get('high_52w_ratio', 0)
            breakout = "✅ 돌파" if stock.get('breakout_20d', False) else "❌ 미돌파"
            bullish = "✅ 발생" if stock.get('has_bullish_candle', False) else "❌ 없음"
            price_chg_3d = stock.get('price_change_3d', 0)

            stock_info = f"""### 종목 {i}: {stock.get('stock_name', '')} ({code})
**정량 지표:**
- PBR: {stock.get('pbr', 'N/A')}, PER: {stock.get('per', 'N/A')}
- RSI(14): {stock.get('rsi_14', 'N/A')}
- 이격도(20일): {stock.get('disparity_20', 'N/A')}%
- 연기금 순매수: {stock.get('pension_net_buy', 0):,}원
- 기관 순매수: {stock.get('institution_net_buy', 0):,}원
- 정량 점수: {stock.get('quant_score', 0)}점

**🚀 모멘텀 지표 (NEW):**
- 거래량 급증: {vol_surge:.1f}배 (5일 평균 대비)
- 거래대금: {trading_val / 100_000_000:.0f}억원
- 이평선: {ma_aligned} (주가 > 5일선 > 20일선)
- 52주 고가 대비: {high_52w * 100:.1f}%
- 20일 신고가: {breakout}
- 장대양봉(3%+): {bullish}
- 3일 상승률: {price_chg_3d:.1f}%
- 모멘텀 점수: {stock.get('momentum_score', 0)}점

**최근 뉴스:**
{news_text}

**컨센서스:**
{consensus_text}

**정책 관련 키워드:** {policy_text}
"""
            stocks_info.append(stock_info)

        stocks_text = "\n\n".join(stocks_info)

        prompt = f"""당신은 한국 주식 시장 전문 애널리스트입니다.
아래 {len(batch)}개 종목에 대해 **급등 가능성**을 중심으로 분석하세요.

**현재 주요 테마 및 정책 (2024-2025):**
- AI/반도체: 엔비디아 수혜, HBM, 파운드리
- 2차전지/배터리: 전고체, 양극재, 음극재
- 방산/우주항공: K-방산 수출, 우주개발, 드론
- 바이오/제약: GLP-1, 신약개발, CMO
- 로봇/자동화: 휴머노이드, 산업용 로봇
- 원전/에너지: SMR, 원전 수출, 전력기기
- 전기차/자율주행: 테슬라 공급망, 라이다
- 게임/콘텐츠: 신작 출시, 글로벌 진출
- 조선/해운: LNG선, 친환경 선박
- K-뷰티/화장품: 중국 리오프닝, 인디 브랜드

{stocks_text}

---

각 종목에 대해 다음 JSON 배열 형식으로 응답하세요. 반드시 유효한 JSON만 출력하세요.

```json
[
  {{
    "code": "종목코드",
    "grade": "S/A/B/C/D",
    "theme": "관련 테마 (AI, 2차전지, 방산 등)",
    "catalyst": "급등 촉매 (구체적인 이벤트/재료)",
    "key_material": "핵심 투자 포인트 (한 문장)",
    "policy_alignment": "정책 수혜 설명 (없으면 '해당없음')",
    "buy_point": "매수 포인트 (한 문장)",
    "risk": "주요 리스크 (한 문장)",
    "confidence": 0.0~1.0 사이 숫자
  }}
]
```

**🔥 등급 기준 (극히 엄격 - 하루 5개 이내 S등급 목표):**

**S등급 (강력 매수) - [모든 조건 충족 필수!]:**
1. [필수] 거래량 급증 3배↑ (5일 평균 대비)
2. [필수] 정배열 상태 (주가 > 5일선 > 20일선)
3. [필수] 20일 신고가 돌파 또는 52주 고가 90%↑
4. [필수] 뉴스에서 명확한 급등 촉매 확인 (수주, 실적, 신사업 발표 등)
5. [필수] 기관/연기금 순매수 (양수)
⚠️ 5개 조건 모두 충족하지 않으면 절대 S등급 불가!
⚠️ 저평가/저PBR만으로는 S등급 절대 불가! 촉매가 핵심!

**A등급 (매수) - [모든 조건 충족 필수!]:**
1. [필수] 거래량 급증 2배↑
2. [필수] 정배열 상태 또는 20일 신고가 돌파
3. [필수] HOT 테마 관련 (AI, 2차전지, 방산, 원전, 바이오 중 하나)
4. [필수] 뉴스에 긍정적 내용 있음
⚠️ 4개 조건 모두 충족해야 A등급!

**B등급 (관심) - 다음 중 2개 이상:**
- 정배열이지만 거래량 부족 (2배 미만)
- 테마 관련 있으나 직접 수혜 불분명
- 52주 고가 대비 70-85% 위치
- 저PBR + 저PER이지만 촉매 없음

**C등급 (중립) - 대부분의 종목:**
- 역배열 상태 (하락 추세)
- 거래량 평이 (급증 없음)
- 테마 무관, 촉매 없음
- 저평가이나 관심 받지 못함

**D등급 (관망):**
- 업황 부진, 실적 악화, 뉴스 부정적
- 52주 저가 근접, 지지선 붕괴
- 거래량 극히 저조

**⚠️ 핵심 원칙 (최상위 종목만 S/A등급!):**
1. S등급은 5개 조건 모두 충족한 '완벽한 종목'만! (하루 최대 3-5개)
2. 저평가만으로는 절대 S/A등급 불가! 반드시 '움직이는 징후 + 촉매' 필요
3. 거래량 급증 없으면 S등급 불가! (최소 3배↑)
4. 역배열 종목은 아무리 좋아도 C등급 이하!
5. 뉴스에서 명확한 촉매를 찾지 못하면 B등급 이하!
6. 의심스러우면 낮은 등급 부여! (보수적 평가)

**등급 부여 순서:**
1. 먼저 모든 종목을 C등급으로 시작
2. S등급 5개 조건 모두 충족? → S등급 (극히 드물어야 함!)
3. A등급 4개 조건 모두 충족? → A등급 (하루 10개 이내)
4. B등급 조건 2개 이상? → B등급
5. 나머지는 C등급 또는 D등급

**주의사항:**
- 거래량 2배 미만이면 S/A등급 불가
- 역배열 종목은 최대 C등급
- 확실한 촉매 없으면 최대 B등급
- confidence: S등급은 0.8↑, A등급은 0.7↑, B등급은 0.5↑
"""

        return prompt

    def _parse_batch_response(
        self,
        response_text: str,
        batch: List[Dict]
    ) -> List[Dict]:
        """Gemini 응답 파싱"""
        try:
            # JSON 추출 (코드 블록 내부)
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 코드 블록 없이 JSON만 있는 경우
                json_str = response_text

            # JSON 파싱
            ai_results = json.loads(json_str)

            # 결과 매핑
            results = []
            ai_map = {r['code']: r for r in ai_results if 'code' in r}

            for stock in batch:
                code = stock['stock_code']
                ai_data = ai_map.get(code, {})

                result = {
                    **stock,
                    'ai_grade': ai_data.get('grade', 'C'),
                    'ai_confidence': float(ai_data.get('confidence', 0.5)),
                    'ai_theme': ai_data.get('theme', ''),
                    'ai_catalyst': ai_data.get('catalyst', ''),
                    'ai_key_material': ai_data.get('key_material', ''),
                    'ai_policy_alignment': ai_data.get('policy_alignment', ''),
                    'ai_buy_point': ai_data.get('buy_point', ''),
                    'ai_risk_factor': ai_data.get('risk', ''),
                    'ai_raw_response': ai_data,
                }
                results.append(result)

            return results

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            logger.debug(f"원본 응답: {response_text[:500]}...")
            return self._assign_default_grades(batch)

    def _assign_default_grades(self, batch: List[Dict]) -> List[Dict]:
        """기본 등급 할당 (API 실패 시)"""
        results = []

        for stock in batch:
            # 정량 점수 기반 기본 등급
            quant_score = stock.get('quant_score', 0)

            if quant_score >= 70:
                grade = 'B'
            elif quant_score >= 50:
                grade = 'C'
            else:
                grade = 'C'

            result = {
                **stock,
                'ai_grade': grade,
                'ai_confidence': 0.3,  # 낮은 확신도
                'ai_key_material': '정량 지표 기반 평가 (AI 분석 불가)',
                'ai_policy_alignment': '해당없음',
                'ai_buy_point': f'정량 점수 {quant_score}점',
                'ai_risk_factor': 'AI 분석 실패로 정성적 평가 불가',
                'ai_raw_response': {'fallback': True},
            }
            results.append(result)

        return results

    async def analyze_single(
        self,
        stock: Dict[str, Any],
        collected: CollectedData
    ) -> Dict[str, Any]:
        """
        단일 종목 재분석 (피드백용)

        Args:
            stock: 종목 정보
            collected: 수집 데이터

        Returns:
            AI 분석 결과
        """
        if not self.model:
            return self._assign_default_grades([stock])[0]

        # 단일 종목용 프롬프트
        batch_results = await self._analyze_single_batch(
            [stock],
            {stock['stock_code']: collected}
        )

        return batch_results[0] if batch_results else self._assign_default_grades([stock])[0]


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    from 신규종목추천.src.utils.database import db
    from 신규종목추천.src.phase1 import Phase1AFilter, Phase1BFilter
    from 신규종목추천.src.phase2.batch_collector import BatchCollector

    await db.connect()

    try:
        # Phase 1 실행
        filter_1a = Phase1AFilter()
        candidates_1a = await filter_1a.filter()

        filter_1b = Phase1BFilter()
        candidates_1b = await filter_1b.filter(candidates_1a)

        # 테스트용 5개만
        test_candidates = candidates_1b[:5]
        print(f"\n=== 테스트: {len(test_candidates)}개 종목 ===\n")

        # Phase 2A
        async with BatchCollector() as collector:
            collected = await collector.collect_all(test_candidates)

        # Phase 2B
        analyzer = GeminiBatchAnalyzer()
        results = await analyzer.analyze_batch(test_candidates, collected)

        print(f"\n=== Phase 2B 결과 ===")
        for r in results:
            print(f"\n{r['stock_code']} {r.get('stock_name', '')}:")
            print(f"  등급: {r.get('ai_grade', 'N/A')} (확신도: {r.get('ai_confidence', 0):.2f})")
            print(f"  핵심: {r.get('ai_key_material', '')}")
            print(f"  정책: {r.get('ai_policy_alignment', '')}")
            print(f"  매수포인트: {r.get('ai_buy_point', '')}")
            print(f"  리스크: {r.get('ai_risk_factor', '')}")

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
