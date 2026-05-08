# -*- coding: utf-8 -*-
"""샘플 면접 데이터 생성 스크립트.

interviews.db 파일에 샘플 면접 기록을 삽입하여
제출용 데이터베이스를 생성한다.

사용법:
    python generate_sample_data.py
"""

import sys
import os

# 현재 디렉토리를 모듈 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import InterviewDB


SAMPLE_INTERVIEWS = [
    {
        "job_field": "반도체",
        "question": "MOSFET의 동작 원리를 간단히 설명해주세요.",
        "answer": "MOSFET은 Metal-Oxide-Semiconductor Field-Effect Transistor의 약자로, 게이트에 전압을 인가하면 산화막 아래에 채널이 형성되어 소스와 드레인 사이에 전류가 흐르게 됩니다. N-channel MOSFET의 경우 게이트에 양의 전압을 인가하면 반전층이 형성되어 전자가 이동할 수 있는 채널이 만들어집니다.",
        "feedback": "📊 논리성 점수: 78/100\n\n✅ 포함된 키워드: MOSFET, 게이트, 채널, 소스, 드레인, 산화막, 반전층\n\n💡 개선점:\n- threshold voltage 개념을 추가하면 좋겠습니다\n- enhancement mode와 depletion mode의 차이도 언급하면 더 완성도 높은 답변이 됩니다\n\n📝 모범 답변:\nMOSFET은 게이트 전압으로 채널의 전도도를 제어하는 트랜지스터입니다. 게이트에 문턱전압(Vth) 이상의 전압을 인가하면 산화막 아래 반도체 표면에 반전층이 형성되어 소스-드레인 간 전류가 흐릅니다.",
        "score": 78,
    },
    {
        "job_field": "반도체",
        "question": "CVD와 PVD의 차이점을 설명해주세요.",
        "answer": "CVD는 Chemical Vapor Deposition으로 화학적 반응을 이용해 박막을 증착하는 방법이고, PVD는 Physical Vapor Deposition으로 물리적 방법을 이용합니다. CVD는 균일한 박막 형성이 가능하고 step coverage가 좋지만, PVD는 고순도 박막을 얻을 수 있습니다.",
        "feedback": "📊 논리성 점수: 82/100\n\n✅ 포함된 키워드: CVD, PVD, 화학적, 물리적, 박막, 증착, step coverage\n\n💡 개선점:\n- 각 방법의 구체적인 예시(스퍼터링, PECVD 등)를 추가하면 좋겠습니다\n- 온도 조건의 차이도 언급하면 더 좋습니다\n\n📝 모범 답변:\nCVD는 가스 상태의 전구체를 화학 반응시켜 박막을 형성하며, step coverage가 우수하고 대면적 균일 증착이 가능합니다. PVD는 스퍼터링이나 증발법으로 물리적으로 박막을 형성하며, 저온 공정이 가능하고 고순도 금속 박막에 적합합니다.",
        "score": 82,
    },
    {
        "job_field": "백엔드",
        "question": "REST API와 GraphQL의 차이점과 각각의 장단점을 설명해주세요.",
        "answer": "REST API는 리소스 기반으로 URL을 설계하고 HTTP 메서드를 활용합니다. GraphQL은 클라이언트가 필요한 데이터만 요청할 수 있어 over-fetching 문제를 해결합니다. REST는 캐싱이 쉽고 단순하지만, GraphQL은 하나의 엔드포인트로 유연한 쿼리가 가능합니다.",
        "feedback": "📊 논리성 점수: 85/100\n\n✅ 포함된 키워드: REST, GraphQL, 리소스, HTTP, over-fetching, 캐싱, 엔드포인트\n\n💡 개선점:\n- under-fetching 문제도 함께 설명하면 좋겠습니다\n- 실무에서 어떤 상황에 각각을 선택하는지 기준을 제시하면 더 좋습니다\n\n📝 모범 답변:\nREST는 리소스별 엔드포인트를 제공하여 구조가 단순하고 HTTP 캐싱을 활용할 수 있지만, 여러 리소스를 조합할 때 다수의 요청이 필요합니다. GraphQL은 단일 엔드포인트에서 클라이언트가 필요한 데이터 구조를 정의하여 요청하므로 over/under-fetching을 방지할 수 있습니다.",
        "score": 85,
    },
    {
        "job_field": "백엔드",
        "question": "트랜잭션의 ACID 속성을 설명하고 실무 예시를 들어주세요.",
        "answer": "ACID는 Atomicity, Consistency, Isolation, Durability의 약자입니다. 원자성은 트랜잭션이 모두 성공하거나 모두 실패해야 한다는 것이고, 일관성은 트랜잭션 전후로 데이터가 일관된 상태를 유지해야 합니다. 격리성은 동시에 실행되는 트랜잭션이 서로 영향을 주지 않아야 하고, 지속성은 커밋된 데이터가 영구적으로 저장되어야 합니다. 예를 들어 은행 송금에서 출금과 입금이 하나의 트랜잭션으로 처리되어야 합니다.",
        "feedback": "📊 논리성 점수: 90/100\n\n✅ 포함된 키워드: ACID, Atomicity, Consistency, Isolation, Durability, 트랜잭션, 커밋\n\n💡 개선점:\n- 격리 수준(Isolation Level)에 대해서도 언급하면 더 깊이 있는 답변이 됩니다\n- 실무에서 발생할 수 있는 동시성 문제(Dirty Read, Phantom Read 등)도 추가하면 좋습니다\n\n📝 모범 답변:\nACID는 데이터베이스 트랜잭션의 4가지 핵심 속성입니다. 은행 송금 예시에서 A계좌 출금과 B계좌 입금은 원자적으로 처리되어야 하며(Atomicity), 총 잔액은 변하지 않아야 하고(Consistency), 다른 트랜잭션과 독립적으로 실행되어야 하며(Isolation), 완료된 송금은 시스템 장애에도 유지되어야 합니다(Durability).",
        "score": 90,
    },
    {
        "job_field": "데이터",
        "question": "정규화와 비정규화의 차이점과 각각 언제 사용하는지 설명해주세요.",
        "answer": "정규화는 데이터 중복을 제거하고 이상현상을 방지하기 위해 테이블을 분리하는 과정입니다. 비정규화는 성능 향상을 위해 의도적으로 중복을 허용하는 것입니다. 정규화는 OLTP 시스템에서, 비정규화는 읽기 성능이 중요한 OLAP이나 데이터 웨어하우스에서 주로 사용합니다.",
        "feedback": "📊 논리성 점수: 87/100\n\n✅ 포함된 키워드: 정규화, 비정규화, 중복, 이상현상, OLTP, OLAP, 데이터 웨어하우스\n\n💡 개선점:\n- 정규화 단계(1NF, 2NF, 3NF)에 대한 간단한 설명을 추가하면 좋겠습니다\n- 비정규화의 구체적인 기법(반복 그룹, 계산 컬럼 등)을 언급하면 더 좋습니다\n\n📝 모범 답변:\n정규화는 함수적 종속성을 기반으로 테이블을 분해하여 삽입/수정/삭제 이상을 방지합니다. 비정규화는 JOIN 비용을 줄이기 위해 의도적으로 중복 데이터를 유지합니다. OLTP에서는 정규화로 데이터 무결성을, 분석용 시스템에서는 비정규화로 조회 성능을 확보합니다.",
        "score": 87,
    },
    {
        "job_field": "데이터",
        "question": "ETL 파이프라인 설계 시 고려해야 할 사항을 설명해주세요.",
        "answer": "ETL은 Extract, Transform, Load의 약자로 데이터를 추출, 변환, 적재하는 과정입니다. 설계 시 데이터 소스의 다양성, 변환 로직의 복잡도, 에러 핸들링, 스케줄링, 모니터링을 고려해야 합니다. 또한 멱등성을 보장하여 재실행 시에도 동일한 결과를 얻을 수 있어야 합니다.",
        "feedback": "📊 논리성 점수: 80/100\n\n✅ 포함된 키워드: ETL, Extract, Transform, Load, 멱등성, 에러 핸들링, 모니터링\n\n💡 개선점:\n- 데이터 품질 검증(Data Validation) 단계를 추가하면 좋겠습니다\n- ELT 패턴과의 비교도 언급하면 더 좋습니다\n- 구체적인 도구(Airflow, Spark 등) 경험을 언급하면 실무 역량을 어필할 수 있습니다\n\n📝 모범 답변:\nETL 파이프라인 설계 시 핵심 고려사항은: 1) 소스 시스템 부하 최소화를 위한 증분 추출, 2) 스키마 변경에 대응하는 유연한 변환 로직, 3) 실패 시 재처리가 가능한 멱등성 보장, 4) 데이터 품질 검증 게이트, 5) 실시간 모니터링 및 알림 체계입니다.",
        "score": 80,
    },
    {
        "job_field": "마케팅",
        "question": "퍼포먼스 마케팅에서 ROAS와 ROI의 차이를 설명해주세요.",
        "answer": "ROAS는 Return On Ad Spend로 광고비 대비 매출을 나타내고, ROI는 Return On Investment로 투자 대비 순이익을 나타냅니다. ROAS가 400%라면 광고비 1원당 4원의 매출이 발생한 것이고, ROI는 광고비뿐 아니라 인건비, 제작비 등 전체 비용을 고려합니다.",
        "feedback": "📊 논리성 점수: 83/100\n\n✅ 포함된 키워드: ROAS, ROI, 광고비, 매출, 순이익, 투자\n\n💡 개선점:\n- 각 지표를 언제 사용하는 것이 적절한지 상황별 설명을 추가하면 좋겠습니다\n- 업계 평균 ROAS 기준이나 목표 설정 방법도 언급하면 좋습니다\n\n📝 모범 답변:\nROAS는 광고 매체별 효율을 빠르게 판단하는 지표로, 매출/광고비로 계산합니다. ROI는 전체 마케팅 활동의 수익성을 평가하며, (순이익-총비용)/총비용으로 계산합니다. 일반적으로 ROAS는 캠페인 최적화에, ROI는 전체 마케팅 전략 평가에 활용합니다.",
        "score": 83,
    },
    {
        "job_field": "마케팅",
        "question": "고객 퍼널(Funnel) 분석의 각 단계와 개선 전략을 설명해주세요.",
        "answer": "고객 퍼널은 인지-관심-고려-구매-충성 단계로 구성됩니다. 각 단계에서 이탈률을 분석하여 병목 구간을 찾고 개선합니다. 인지 단계에서는 광고 도달률을, 구매 단계에서는 전환율을 높이는 전략을 사용합니다. 충성 단계에서는 재구매율과 추천을 유도합니다.",
        "feedback": "📊 논리성 점수: 76/100\n\n✅ 포함된 키워드: 퍼널, 인지, 관심, 구매, 충성, 이탈률, 전환율\n\n💡 개선점:\n- 각 단계별 구체적인 KPI와 개선 액션을 더 상세히 설명하면 좋겠습니다\n- AARRR 프레임워크와의 연관성도 언급하면 좋습니다\n- 실제 데이터 분석 도구(GA, Amplitude 등) 활용 경험을 추가하면 좋습니다\n\n📝 모범 답변:\n고객 퍼널은 TOFU(인지)-MOFU(고려)-BOFU(전환)-Retention(유지)으로 구분합니다. 각 단계별 전략: 인지 단계는 SEO/광고로 유입 확대, 고려 단계는 콘텐츠/리뷰로 신뢰 구축, 전환 단계는 CTA 최적화/프로모션, 유지 단계는 CRM/로열티 프로그램으로 LTV를 극대화합니다.",
        "score": 76,
    },
]


def main():
    """샘플 데이터를 생성하여 interviews.db에 저장."""
    # 기존 DB 파일이 있으면 삭제하고 새로 생성
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interviews.db")

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"기존 데이터베이스 삭제: {db_path}")

    # 데이터베이스 초기화 (테이블 생성 + 기출 질문 시드)
    db = InterviewDB(db_path)

    # 샘플 면접 기록 삽입
    for i, record in enumerate(SAMPLE_INTERVIEWS, 1):
        db.save_interview(
            job_field=record["job_field"],
            question=record["question"],
            answer=record["answer"],
            feedback=record["feedback"],
            score=record["score"],
        )
        print(f"  [{i}/{len(SAMPLE_INTERVIEWS)}] {record['job_field']} - {record['question'][:30]}...")

    # 결과 확인
    stats = db.get_stats()
    print(f"\n✅ 샘플 데이터 생성 완료!")
    print(f"   - 총 면접 기록: {stats['total_interviews']}건")
    print(f"   - 평균 점수: {stats['avg_score']}점")
    print(f"   - 직무별 분포: {stats['job_distribution']}")
    print(f"   - 질문 뱅크 크기: {stats['question_bank_size']}개")
    print(f"   - 데이터베이스 경로: {db_path}")

    db.close()


if __name__ == "__main__":
    main()
