"""
Phase 4: AI 회고 (Retrospective)

실패한 추천 종목(-5% 이하)에 대해 AI가 스스로 분석하여
"왜 틀렸는지", "놓친 리스크가 무엇인지"를 학습합니다.

목표:
- 당시 분석에서 놓친 리스크 식별
- 실제 하락 원인 파악
- 향후 분석 개선을 위한 교훈 도출
"""
import asyncio
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

import google.generativeai as genai

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db
from 신규종목추천.src.phase4.profit_tracker import ProfitTracker

logger = logging.getLogger(__name__)


class AIRetrospective:
    """
    AI 회고 분석기

    실패한 추천에 대해 Gemini AI가 당시 분석의 문제점을
    스스로 분석하고 교훈을 도출합니다.
    """

    # 실패 기준 (손실률)
    FAILURE_THRESHOLD = -5.0  # -5% 이하

    def __init__(self):
        self.config = settings.phase2b
        genai.configure(api_key=self.config.api_key)
        self.model = genai.GenerativeModel(self.config.model_name)
        logger.info(f"AI 회고 분석기 초기화: {self.config.model_name}")

    async def analyze_failures(self, limit: int = 10) -> Dict[str, Any]:
        """
        실패한 추천들에 대해 AI 회고 분석 실행

        Args:
            limit: 분석할 최대 종목 수

        Returns:
            분석 결과 요약
        """
        logger.info(f"=== AI 회고 분석 시작 (최대 {limit}건) ===")
        start_time = datetime.now()

        # 1. 실패 종목 조회 (아직 회고 분석 안 된 것)
        failed_stocks = await self._get_unanalyzed_failures(limit)

        if not failed_stocks:
            logger.info("분석 대상 실패 종목 없음")
            return {'analyzed_count': 0, 'lessons': []}

        logger.info(f"{len(failed_stocks)}개 실패 종목 분석 대상")

        # 2. 각 종목에 대해 회고 분석
        analyzed_count = 0
        lessons = []

        for stock in failed_stocks:
            try:
                result = await self._analyze_single_failure(stock)
                if result:
                    analyzed_count += 1
                    lessons.append(result)
                    logger.info(f"  - {stock['stock_name']}: 회고 완료")

                # Rate limit 대기
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"{stock['stock_code']} 회고 분석 실패: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== AI 회고 완료: {analyzed_count}건 ({elapsed:.1f}초) ===")

        # 3. 공통 교훈 추출
        common_lessons = self._extract_common_lessons(lessons)

        return {
            'analyzed_count': analyzed_count,
            'lessons': lessons,
            'common_lessons': common_lessons
        }

    async def _get_unanalyzed_failures(self, limit: int) -> List[Dict]:
        """아직 회고 분석되지 않은 실패 종목 조회"""

        query = """
        SELECT
            sp.id as performance_id,
            sp.recommendation_id,
            sp.stock_code,
            sr.stock_name,
            sp.rec_date,
            sp.rec_price,
            sp.check_date,
            sp.check_price,
            sp.return_rate,
            sp.max_drawdown,
            sp.days_held,
            sr.ai_grade,
            sr.ai_key_material,
            sr.ai_policy_alignment,
            sr.ai_buy_point,
            sr.ai_risk_factor,
            sr.ai_raw_response,
            sr.final_score
        FROM smart_performance sp
        JOIN smart_recommendations sr ON sp.recommendation_id = sr.id
        LEFT JOIN smart_ai_retrospective sar ON sp.id = sar.performance_id
        WHERE sp.return_rate <= $1
          AND sp.status = 'failed'
          AND sar.id IS NULL  -- 아직 회고 안된 것
        ORDER BY sp.return_rate ASC
        LIMIT $2
        """

        return await db.fetch(query, self.FAILURE_THRESHOLD, limit)

    async def _analyze_single_failure(self, stock: Dict) -> Optional[Dict]:
        """단일 실패 종목에 대한 AI 회고 분석"""

        # 해당 기간의 뉴스/악재 조회
        bad_news = await self._get_subsequent_news(
            stock['stock_code'],
            stock['rec_date'],
            stock['check_date']
        )

        # 프롬프트 생성
        prompt = self._build_retrospective_prompt(stock, bad_news)

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_retrospective_response(response.text)

            # DB 저장
            await self._save_retrospective(stock, result, response.text)

            return {
                'stock_code': stock['stock_code'],
                'stock_name': stock['stock_name'],
                'return_rate': float(stock['return_rate']),
                **result
            }

        except Exception as e:
            logger.error(f"Gemini 회고 분석 실패: {e}")
            return None

    def _build_retrospective_prompt(self, stock: Dict, bad_news: List[Dict]) -> str:
        """회고 분석용 프롬프트 생성"""

        news_text = ""
        if bad_news:
            news_text = "\n".join([
                f"- [{n['published_date']}] {n['title']}"
                for n in bad_news[:10]
            ])
        else:
            news_text = "(뉴스 데이터 없음)"

        return f"""당신은 주식 투자 AI 분석가입니다. 아래는 당신이 과거에 추천했지만 실패한 종목입니다.
왜 틀렸는지 스스로 분석하고, 향후 개선점을 도출하세요.

## 추천 당시 정보
- **종목**: {stock['stock_name']} ({stock['stock_code']})
- **추천일**: {stock['rec_date']}
- **추천가**: {stock['rec_price']:,}원
- **AI등급**: {stock['ai_grade']}
- **최종점수**: {stock.get('final_score', 'N/A')}

## 당시 AI 분석
- **핵심 재료**: {stock.get('ai_key_material', 'N/A')}
- **정책 관련**: {stock.get('ai_policy_alignment', 'N/A')}
- **매수 포인트**: {stock.get('ai_buy_point', 'N/A')}
- **리스크 요인**: {stock.get('ai_risk_factor', 'N/A')}

## 실제 결과
- **확인일**: {stock['check_date']}
- **현재가**: {stock['check_price']:,}원
- **수익률**: {stock['return_rate']:+.2f}%
- **최대 손실**: {stock.get('max_drawdown', 'N/A')}%
- **보유 기간**: {stock['days_held']}일

## 추천 이후 관련 뉴스
{news_text}

---

위 정보를 바탕으로 다음 질문에 답하세요:

1. **놓친 리스크**: 당시 분석에서 간과한 리스크 요인은 무엇인가요?
2. **실제 원인**: 주가 하락의 실제 원인은 무엇으로 추정되나요?
3. **학습 교훈**: 이 실패에서 배울 수 있는 교훈은 무엇인가요?
4. **개선 제안**: 향후 이런 실수를 줄이기 위한 분석 개선점은?
5. **신뢰도 조정**: 이 유형의 종목/상황에 대한 신뢰도를 어떻게 조정해야 할까요? (-10 ~ +10)

**반드시 아래 JSON 형식으로만 응답하세요:**
```json
{{
  "missed_risks": "놓친 리스크 설명",
  "actual_cause": "실제 하락 원인",
  "lesson_learned": "학습된 교훈",
  "improvement_suggestion": "개선 제안",
  "confidence_adjustment": -5
}}
```
"""

    async def _get_subsequent_news(self, stock_code: str,
                                    rec_date: date,
                                    check_date: date) -> List[Dict]:
        """추천 이후 해당 종목 관련 뉴스 조회"""

        # collected_data에서 뉴스 조회 시도
        query = """
        SELECT
            (data_content->>'title') as title,
            (data_content->>'published_date') as published_date,
            (data_content->>'sentiment') as sentiment
        FROM collected_data
        WHERE stock_code = $1
          AND data_type IN ('news', 'news_naver', 'news_daum')
          AND collected_at > $2
          AND collected_at <= $3
        ORDER BY collected_at DESC
        LIMIT 10
        """

        try:
            news = await db.fetch(query, stock_code, rec_date, check_date)
            return news if news else []
        except:
            return []

    def _parse_retrospective_response(self, response_text: str) -> Dict[str, Any]:
        """AI 응답 파싱"""

        # JSON 블록 추출
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)

        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # JSON 블록 없이 직접 파싱 시도
        try:
            # { } 사이의 내용 추출
            brace_match = re.search(r'\{[\s\S]*\}', response_text)
            if brace_match:
                return json.loads(brace_match.group())
        except:
            pass

        # 파싱 실패 시 기본값
        return {
            'missed_risks': '파싱 실패',
            'actual_cause': '파싱 실패',
            'lesson_learned': '파싱 실패',
            'improvement_suggestion': '파싱 실패',
            'confidence_adjustment': 0
        }

    async def _save_retrospective(self, stock: Dict, result: Dict,
                                   raw_response: str) -> None:
        """회고 분석 결과 DB 저장"""

        query = """
        INSERT INTO smart_ai_retrospective
            (performance_id, recommendation_id, stock_code, stock_name,
             rec_date, rec_grade, rec_score, original_key_material, original_risk_factor,
             actual_return, max_drawdown, days_held,
             missed_risks, actual_cause, lesson_learned, improvement_suggestion,
             confidence_adjustment, ai_raw_response)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        """

        await db.execute(
            query,
            stock['performance_id'],
            stock['recommendation_id'],
            stock['stock_code'],
            stock['stock_name'],
            stock['rec_date'],
            stock['ai_grade'],
            stock.get('final_score'),
            stock.get('ai_key_material'),
            stock.get('ai_risk_factor'),
            stock['return_rate'],
            stock.get('max_drawdown'),
            stock['days_held'],
            result.get('missed_risks'),
            result.get('actual_cause'),
            result.get('lesson_learned'),
            result.get('improvement_suggestion'),
            result.get('confidence_adjustment'),
            json.dumps({'raw': raw_response})
        )

    def _extract_common_lessons(self, lessons: List[Dict]) -> Dict[str, Any]:
        """여러 실패 분석에서 공통 교훈 추출"""

        if not lessons:
            return {}

        # 간단한 키워드 빈도 분석
        risk_keywords = {}
        cause_keywords = {}

        for lesson in lessons:
            # 놓친 리스크 키워드
            risks = lesson.get('missed_risks', '')
            for word in ['유동성', '변동성', '업황', '경쟁', '실적', '거래량', '과열']:
                if word in risks:
                    risk_keywords[word] = risk_keywords.get(word, 0) + 1

            # 원인 키워드
            cause = lesson.get('actual_cause', '')
            for word in ['실적', '하락', '악재', '경기', '금리', '수급', '테마']:
                if word in cause:
                    cause_keywords[word] = cause_keywords.get(word, 0) + 1

        return {
            'total_failures': len(lessons),
            'avg_loss': sum(l['return_rate'] for l in lessons) / len(lessons),
            'common_missed_risks': sorted(risk_keywords.items(), key=lambda x: -x[1])[:5],
            'common_causes': sorted(cause_keywords.items(), key=lambda x: -x[1])[:5]
        }

    async def generate_learning_report(self) -> str:
        """AI 회고 학습 리포트 생성"""

        # 최근 회고 분석 결과 조회
        query = """
        SELECT
            stock_code,
            stock_name,
            rec_date,
            rec_grade,
            actual_return,
            missed_risks,
            actual_cause,
            lesson_learned,
            improvement_suggestion,
            confidence_adjustment
        FROM smart_ai_retrospective
        ORDER BY analyzed_at DESC
        LIMIT 20
        """

        retrospectives = await db.fetch(query)

        if not retrospectives:
            return "# AI 회고 리포트\n\n분석된 회고 데이터가 없습니다."

        report = "# AI 회고 학습 리포트\n\n"
        report += f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report += f"**분석 건수**: {len(retrospectives)}건\n\n"

        report += "## 📊 실패 분석 요약\n\n"
        report += "| 종목 | 등급 | 수익률 | 놓친 리스크 | 교훈 |\n"
        report += "|:---|:---:|:---:|:---|:---|\n"

        for r in retrospectives[:10]:
            missed = (r['missed_risks'] or '')[:30] + '...' if len(r.get('missed_risks', '') or '') > 30 else r.get('missed_risks', 'N/A')
            lesson = (r['lesson_learned'] or '')[:30] + '...' if len(r.get('lesson_learned', '') or '') > 30 else r.get('lesson_learned', 'N/A')
            report += f"| {r['stock_name']} | {r['rec_grade']} | {r['actual_return']:+.1f}% | {missed} | {lesson} |\n"

        # 공통 교훈
        report += "\n## 🎯 공통 교훈\n\n"

        # 신뢰도 조정 평균
        avg_adjustment = sum(r.get('confidence_adjustment', 0) or 0 for r in retrospectives) / len(retrospectives)
        report += f"- **평균 신뢰도 조정**: {avg_adjustment:+.1f}\n"
        report += f"- **평균 손실률**: {sum(r['actual_return'] for r in retrospectives) / len(retrospectives):.1f}%\n"

        return report


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await db.connect()

    try:
        # 먼저 수익률 추적
        tracker = ProfitTracker()
        await tracker.track_all()

        # AI 회고 분석
        retrospective = AIRetrospective()
        results = await retrospective.analyze_failures(limit=5)

        print(f"\n=== AI 회고 분석 결과 ===")
        print(f"분석 건수: {results['analyzed_count']}")

        if results.get('common_lessons'):
            cl = results['common_lessons']
            print(f"\n공통 교훈:")
            print(f"  - 총 실패: {cl.get('total_failures')}건")
            print(f"  - 평균 손실: {cl.get('avg_loss', 0):.1f}%")
            print(f"  - 자주 놓친 리스크: {cl.get('common_missed_risks')}")

        # 리포트 생성
        report = await retrospective.generate_learning_report()
        print("\n" + report)

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
