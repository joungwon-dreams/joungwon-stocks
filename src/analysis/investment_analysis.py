"""
투자 포인트 분석 모듈

재무 데이터와 시장 데이터를 기반으로 투자 포인트를 생성합니다.
"""
from typing import Dict, List, Any, Optional


def analyze_financial_health(financials: Dict[str, Any]) -> List[str]:
    """재무 건전성 분석"""
    points = []

    revenue = financials.get('revenue', [])
    op_profit = financials.get('operating_profit', [])
    net_profit = financials.get('net_profit', [])
    roe = financials.get('roe', [])

    # 매출 성장성
    if len(revenue) >= 2:
        recent_revenue = [r for r in revenue[-2:] if r and r > 0]
        if len(recent_revenue) == 2:
            growth_rate = ((recent_revenue[-1] - recent_revenue[-2]) / recent_revenue[-2]) * 100
            if growth_rate > 10:
                points.append(f"✅ 매출 성장세 양호 (최근 {growth_rate:.1f}% 증가)")
            elif growth_rate > 0:
                points.append(f"✓ 매출 안정적 성장 ({growth_rate:.1f}% 증가)")
            else:
                points.append(f"⚠️ 매출 감소 추세 ({growth_rate:.1f}% 감소)")

    # 영업이익 흑자 전환
    if len(op_profit) >= 2:
        recent_ops = op_profit[-2:]
        if all(p is not None for p in recent_ops):
            if recent_ops[-2] < 0 and recent_ops[-1] > 0:
                points.append("✅ 영업이익 흑자 전환 성공")
            elif recent_ops[-1] > 0:
                op_growth = ((recent_ops[-1] - recent_ops[-2]) / abs(recent_ops[-2])) * 100
                if op_growth > 20:
                    points.append(f"✅ 영업이익 대폭 개선 ({op_growth:.1f}% 증가)")

    # ROE 개선
    if len(roe) >= 2:
        recent_roes = [r for r in roe[-2:] if r is not None]
        if len(recent_roes) == 2:
            if recent_roes[-2] < 0 and recent_roes[-1] > 0:
                points.append("✅ ROE 흑자 전환")
            elif recent_roes[-1] > 15:
                points.append(f"✅ 우수한 자기자본이익률 (ROE {recent_roes[-1]:.1f}%)")
            elif recent_roes[-1] > recent_roes[-2]:
                points.append(f"✓ ROE 개선 추세 ({recent_roes[-1]:.1f}%)")

    return points


def analyze_valuation(metrics: Dict[str, Any], financials: Dict[str, Any]) -> List[str]:
    """밸류에이션 분석"""
    points = []

    per = metrics.get('per')
    pbr = metrics.get('pbr')

    # PER 분석
    if per and per > 0:
        if per < 5:
            points.append(f"✅ 매우 저평가 상태 (PER {per:.2f}배)")
        elif per < 10:
            points.append(f"✓ 저평가 구간 (PER {per:.2f}배)")
        elif per < 15:
            points.append(f"적정 밸류에이션 (PER {per:.2f}배)")
        else:
            points.append(f"⚠️ 높은 밸류에이션 (PER {per:.2f}배)")

    # PBR 분석
    if pbr and pbr > 0:
        if pbr < 0.5:
            points.append(f"✅ 순자산 대비 매우 저평가 (PBR {pbr:.2f}배)")
        elif pbr < 1.0:
            points.append(f"✓ 순자산 대비 저평가 (PBR {pbr:.2f}배)")

    # 배당수익률
    div_yield = metrics.get('dividend_yield')
    if div_yield and div_yield > 0:
        if div_yield >= 3:
            points.append(f"✅ 높은 배당수익률 ({div_yield:.2f}%)")
        elif div_yield >= 2:
            points.append(f"✓ 안정적 배당 ({div_yield:.2f}%)")

    return points


def analyze_analyst_opinion(consensus: Dict[str, Any]) -> List[str]:
    """애널리스트 의견 분석"""
    points = []

    analyst_count = consensus.get('analyst_count', 0)

    if analyst_count > 0:
        points.append(f"📊 {analyst_count}명의 애널리스트가 커버리지 제공")

        if analyst_count >= 40:
            points.append("✓ 시장의 높은 관심도")

    return points


def analyze_future_outlook(financials: Dict[str, Any]) -> List[str]:
    """미래 전망 분석"""
    points = []

    years = financials.get('years', [])
    revenue = financials.get('revenue', [])
    op_profit = financials.get('operating_profit', [])

    # 추정치 포함 여부 확인 (연도에 "E" 포함)
    estimated_indices = [i for i, year in enumerate(years) if 'E' in str(year) or '추정' in str(year)]

    if estimated_indices:
        # 실적 vs 추정 비교
        actual_revenue = [r for i, r in enumerate(revenue) if i < estimated_indices[0] and r]
        estimated_revenue = [r for i, r in enumerate(revenue) if i in estimated_indices and r]

        if actual_revenue and estimated_revenue:
            last_actual = actual_revenue[-1]
            first_estimate = estimated_revenue[0]

            if first_estimate > last_actual:
                growth = ((first_estimate - last_actual) / last_actual) * 100
                points.append(f"📈 향후 매출 성장 전망 ({growth:.1f}% 예상)")

        # 영업이익 추정
        actual_op = [p for i, p in enumerate(op_profit) if i < estimated_indices[0] and p]
        estimated_op = [p for i, p in enumerate(op_profit) if i in estimated_indices and p]

        if actual_op and estimated_op:
            last_actual_op = actual_op[-1]
            first_estimate_op = estimated_op[0]

            if last_actual_op < 0 and first_estimate_op > 0:
                points.append("✅ 영업이익 흑자 지속 전망")
            elif first_estimate_op > last_actual_op:
                points.append("📈 영업이익 개선 지속 전망")

    return points


def generate_investment_points(fnguide_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    투자 포인트 생성

    Args:
        fnguide_data: FnGuide에서 수집한 데이터

    Returns:
        투자 포인트 딕셔너리
    """
    points = {
        'financial_health': [],
        'valuation': [],
        'analyst_opinion': [],
        'future_outlook': [],
        'all_points': []
    }

    if not fnguide_data:
        return points

    # 재무 건전성 분석
    financials = fnguide_data.get('financial_summary', {})
    if financials:
        financial_points = analyze_financial_health(financials)
        points['financial_health'] = financial_points
        points['all_points'].extend(financial_points)

    # 밸류에이션 분석
    metrics = fnguide_data.get('valuation_metrics', {})
    if metrics:
        valuation_points = analyze_valuation(metrics, financials)
        points['valuation'] = valuation_points
        points['all_points'].extend(valuation_points)

    # 애널리스트 의견
    consensus = fnguide_data.get('analyst_consensus', {})
    if consensus:
        analyst_points = analyze_analyst_opinion(consensus)
        points['analyst_opinion'] = analyst_points
        points['all_points'].extend(analyst_points)

    # 미래 전망
    if financials:
        outlook_points = analyze_future_outlook(financials)
        points['future_outlook'] = outlook_points
        points['all_points'].extend(outlook_points)

    return points


def get_investment_recommendation(fnguide_data: Dict[str, Any]) -> str:
    """
    종합 투자 의견 생성

    Args:
        fnguide_data: FnGuide 데이터

    Returns:
        투자 의견 문자열
    """
    if not fnguide_data:
        return "데이터 부족으로 투자 의견을 제시할 수 없습니다."

    points = generate_investment_points(fnguide_data)
    all_points = points['all_points']

    if not all_points:
        return "분석 가능한 데이터가 충분하지 않습니다."

    # 긍정/부정 포인트 개수
    positive_count = sum(1 for p in all_points if '✅' in p or '📈' in p)
    neutral_count = sum(1 for p in all_points if '✓' in p or '📊' in p)
    negative_count = sum(1 for p in all_points if '⚠️' in p)

    total_points = len(all_points)
    positive_ratio = (positive_count + neutral_count * 0.5) / total_points if total_points > 0 else 0

    if positive_ratio >= 0.7:
        return "긍정적인 투자 포인트가 다수 관찰됩니다. 중장기 투자 관점에서 매력적인 종목으로 판단됩니다."
    elif positive_ratio >= 0.5:
        return "안정적인 투자 포인트를 보유하고 있으나, 일부 주의사항이 있습니다. 분산 투자 관점에서 접근을 권장합니다."
    elif positive_ratio >= 0.3:
        return "긍정적 요소와 부정적 요소가 혼재되어 있습니다. 신중한 접근이 필요합니다."
    else:
        return "현재 투자 매력도가 제한적입니다. 추가적인 개선 신호 확인 후 재검토를 권장합니다."
