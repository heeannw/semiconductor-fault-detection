"""공정 파라미터가 규격을 벗어났을 때 원인 후보/영향/조치를 제안하는 규칙 기반 진단.

SECOM 이상 탐지 모델(SHAP)은 "어떤 피처가 판정에 얼마나 기여했는지"는 보여주지만, SECOM
피처 자체가 익명화돼 있어(feature_1, feature_2, ...) 사람이 읽을 수 있는 "핵심 에러 문구"로
바꿀 수 없다 — 이건 이 프로젝트가 고칠 수 없는 데이터셋 자체의 한계다(README/docs/AMHS.md에도
같은 취지로 여러 번 명시했다). 반면 공정 시뮬레이터(`process_simulator.py`)의 파라미터는 실제
이름과 단위, 정상 범위(low/high)가 있으므로, "이 파라미터가 이 방향으로 벗어났다"는 사실만으로도
반도체 공정 도메인 지식에 기반한 원인 후보/영향/조치를 정적 규칙으로 제안할 수 있다.

LLM API를 호출하지 않는다 — 전부 하드코딩된 정적 템플릿이라 비용이 전혀 발생하지 않고,
결과가 항상 결정적(deterministic)이다. 실제 fab에서는 이 템플릿을 공정 엔지니어의 실측
경험/트러블슈팅 매뉴얼로 교체하면 그대로 재사용 가능한 구조다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .process_simulator import PROCESS_SPECS

Direction = str  # "high" | "low"


@dataclass(frozen=True)
class DiagnosisTemplate:
    label: str  # 핵심 에러 문구
    cause: str  # 원인 후보
    impact: str  # 방치 시 영향
    action: str  # 조치 제안


@dataclass(frozen=True)
class Diagnosis:
    process: str
    parameter: str
    value: float
    spec_low: float
    spec_high: float
    unit: str
    direction: Direction
    label: str
    cause: str
    impact: str
    action: str


# (process, parameter, "high" | "low") -> 진단 템플릿. 8개 공정 24개 파라미터 전체를 다룬다.
DIAGNOSIS_TEMPLATES: dict[tuple[str, str, Direction], DiagnosisTemplate] = {
    ("wafer_fabrication", "temperature", "high"): DiagnosisTemplate(
        "웨이퍼 제조 온도 상한 초과", "히터 과열 또는 온도 컨트롤러 드리프트",
        "결정 결함 증가, 웨이퍼 휨(warpage) 위험",
        "히터 캘리브레이션 점검, 냉각 시스템 유량 확인",
    ),
    ("wafer_fabrication", "temperature", "low"): DiagnosisTemplate(
        "웨이퍼 제조 온도 하한 미달", "히터 출력 부족 또는 열전대(TC) 측정 오차",
        "결정 성장 불완전, 저항률 산포 증가",
        "히터 전력 공급 점검, 열전대 교체/재교정",
    ),
    ("wafer_fabrication", "oxygen_concentration", "high"): DiagnosisTemplate(
        "산소 농도 규격 초과", "챔버 퍼지 불충분 또는 시일 누설",
        "표면 산화층 이상 생성, 결정 순도 저하",
        "퍼지 가스 유량 점검, 챔버 시일 누설 검사",
    ),
    ("wafer_fabrication", "oxygen_concentration", "low"): DiagnosisTemplate(
        "산소 농도 센서값 이상", "산소 센서 드리프트 또는 배선 접촉 불량",
        "측정값 자체가 신뢰 불가 — 후속 공정 판단 오류 위험",
        "산소 센서 재교정, 배선 점검",
    ),
    ("wafer_fabrication", "resistivity", "high"): DiagnosisTemplate(
        "저항률 상한 초과", "도판트 농도 부족",
        "소자 동작 특성 이탈, 수율 저하",
        "도핑 공정 파라미터 재검토, 원료 순도 점검",
    ),
    ("wafer_fabrication", "resistivity", "low"): DiagnosisTemplate(
        "저항률 하한 미달", "도판트 과다 주입",
        "누설 전류 증가, 소자 특성 이탈",
        "도핑 농도/시간 재조정",
    ),
    ("oxidation", "temperature", "high"): DiagnosisTemplate(
        "산화 공정 온도 상한 초과", "퍼니스 온도 오버슈트",
        "산화막 과성장, 두께 산포 증가",
        "온도 컨트롤러 PID 재튜닝",
    ),
    ("oxidation", "temperature", "low"): DiagnosisTemplate(
        "산화 공정 온도 하한 미달", "히터 노후화 또는 전력 부족",
        "산화 반응 불완전, 막질 불균일",
        "히터 상태 점검, 전력 공급 확인",
    ),
    ("oxidation", "time", "high"): DiagnosisTemplate(
        "산화 시간 상한 초과", "레시피 타이머 오류 또는 공정 지연",
        "산화막 과성장, 처리량(throughput) 저하",
        "레시피 파라미터 검증, 장비 인터록 확인",
    ),
    ("oxidation", "time", "low"): DiagnosisTemplate(
        "산화 시간 하한 미달", "타이머 조기 종료",
        "산화막 두께 부족, 절연 특성 저하",
        "레시피 시퀀스 재확인",
    ),
    ("oxidation", "oxide_thickness", "high"): DiagnosisTemplate(
        "산화막 두께 상한 초과", "과산화(온도·시간 과다의 결과)",
        "후속 포토/식각 공정 정합성 저하",
        "온도/시간 파라미터 재조정",
    ),
    ("oxidation", "oxide_thickness", "low"): DiagnosisTemplate(
        "산화막 두께 하한 미달", "산화 반응 불충분",
        "절연 파괴 전압 저하, 소자 신뢰성 저하",
        "산화 시간 연장, 가스 유량 점검",
    ),
    ("photolithography", "exposure_energy", "high"): DiagnosisTemplate(
        "노광 에너지 상한 초과", "광원 파워 드리프트",
        "패턴 과다 노광(overexposure), CD(critical dimension) 축소",
        "광원 출력 캘리브레이션",
    ),
    ("photolithography", "exposure_energy", "low"): DiagnosisTemplate(
        "노광 에너지 하한 미달", "광원 노후화 또는 셔터 타이밍 오차",
        "패턴 미달 노광(underexposure), 패턴 브릿지 위험",
        "광원 교체 검토, 셔터 타이밍 점검",
    ),
    ("photolithography", "focus_distance", "high"): DiagnosisTemplate(
        "초점 거리 상한 초과(+)", "웨이퍼 스테이지 레벨링 오차",
        "패턴 흐림(blur), CD 산포 증가",
        "오토포커스 재캘리브레이션",
    ),
    ("photolithography", "focus_distance", "low"): DiagnosisTemplate(
        "초점 거리 하한 미달(-)", "웨이퍼 스테이지 레벨링 오차(반대 방향)",
        "패턴 흐림(blur), CD 산포 증가",
        "오토포커스 재캘리브레이션",
    ),
    ("photolithography", "temperature", "high"): DiagnosisTemplate(
        "포토 공정 온도 상한 초과", "핫플레이트 오버슈트",
        "PR(감광액) 경화 이상, 패턴 프로파일 왜곡",
        "핫플레이트 온도 컨트롤러 점검",
    ),
    ("photolithography", "temperature", "low"): DiagnosisTemplate(
        "포토 공정 온도 하한 미달", "핫플레이트 예열 부족",
        "PR 경화 불충분, 패턴 밀착력 저하",
        "예열 시간 재설정",
    ),
    ("etching", "pressure", "high"): DiagnosisTemplate(
        "식각 압력 상한 초과", "배기 펌프 성능 저하 또는 밸브 드리프트",
        "식각 이방성 저하, CD 산포 증가",
        "펌프 점검, MFC 캘리브레이션",
    ),
    ("etching", "pressure", "low"): DiagnosisTemplate(
        "식각 압력 하한 미달", "챔버 누설 또는 과도 배기",
        "식각 속도 불안정, 균일도 저하",
        "챔버 시일 누설 검사",
    ),
    ("etching", "gas_flow", "high"): DiagnosisTemplate(
        "식각 가스 유량 상한 초과", "MFC(질량유량 컨트롤러) 캘리브레이션 오차",
        "과도 식각(over-etch) 위험, 언더컷 증가",
        "MFC 재교정",
    ),
    ("etching", "gas_flow", "low"): DiagnosisTemplate(
        "식각 가스 유량 하한 미달", "가스 라인 막힘 또는 공급압 부족",
        "식각 속도 저하, 처리량 감소",
        "가스 라인 점검, 공급압 확인",
    ),
    ("etching", "power", "high"): DiagnosisTemplate(
        "식각 파워 상한 초과", "RF 제너레이터 출력 드리프트",
        "플라즈마 손상(plasma damage) 위험, 표면 거칠기 증가",
        "RF 매칭 네트워크 점검",
    ),
    ("etching", "power", "low"): DiagnosisTemplate(
        "식각 파워 하한 미달", "제너레이터 출력 부족 또는 임피던스 매칭 실패",
        "식각 속도 저하, 미달 식각(under-etch) 위험",
        "매칭 네트워크 재조정",
    ),
    ("deposition", "temperature", "high"): DiagnosisTemplate(
        "증착 온도 상한 초과", "히터 오버슈트",
        "막 응력 증가, 균일도 저하",
        "온도 컨트롤러 재튜닝",
    ),
    ("deposition", "temperature", "low"): DiagnosisTemplate(
        "증착 온도 하한 미달", "히터 출력 부족",
        "막질 불균일, 접착력 저하",
        "히터 상태 점검",
    ),
    ("deposition", "pressure", "high"): DiagnosisTemplate(
        "증착 압력 상한 초과", "배기 성능 저하",
        "막 두께 균일도 저하",
        "펌프/밸브 점검",
    ),
    ("deposition", "pressure", "low"): DiagnosisTemplate(
        "증착 압력 하한 미달", "과도 배기 또는 챔버 누설",
        "증착 속도 불안정",
        "챔버 시일 점검",
    ),
    ("deposition", "deposition_rate", "high"): DiagnosisTemplate(
        "증착 속도 상한 초과", "전구체(precursor) 유량 과다",
        "막 두께 산포 증가, 막질 저하",
        "전구체 MFC 재교정",
    ),
    ("deposition", "deposition_rate", "low"): DiagnosisTemplate(
        "증착 속도 하한 미달", "전구체 공급 부족 또는 소스 고갈",
        "처리량 저하, 목표 두께 미달 위험",
        "전구체 소스 잔량 확인",
    ),
    ("metallization", "current_density", "high"): DiagnosisTemplate(
        "전류 밀도 상한 초과", "파워 서플라이 출력 드리프트",
        "배선 균일도 저하, 국부 과도금(overplating)",
        "파워 서플라이 캘리브레이션",
    ),
    ("metallization", "current_density", "low"): DiagnosisTemplate(
        "전류 밀도 하한 미달", "전극 접촉 불량 또는 저항 증가",
        "도금 두께 부족, 배선 저항 증가",
        "전극 접촉 상태 점검",
    ),
    ("metallization", "temperature", "high"): DiagnosisTemplate(
        "도금 온도 상한 초과", "도금액 항온조 컨트롤러 오차",
        "도금막 품질 저하, 배선 신뢰성 저하",
        "항온조 점검",
    ),
    ("metallization", "temperature", "low"): DiagnosisTemplate(
        "도금 온도 하한 미달", "항온조 과냉각",
        "도금 속도 저하, 처리량 감소",
        "항온조 설정값 재확인",
    ),
    ("metallization", "plating_time", "high"): DiagnosisTemplate(
        "도금 시간 상한 초과", "레시피 타이머 오류",
        "과도금(overplating), 배선 단락 위험",
        "레시피 시퀀스 검증",
    ),
    ("metallization", "plating_time", "low"): DiagnosisTemplate(
        "도금 시간 하한 미달", "타이머 조기 종료",
        "도금 두께 부족, 배선 저항 증가",
        "레시피 시퀀스 재확인",
    ),
    ("eds", "test_voltage", "high"): DiagnosisTemplate(
        "EDS 테스트 전압 상한 초과", "테스터 전원 캘리브레이션 오차",
        "소자 과전압 스트레스, 오검출 위험",
        "테스터 재교정",
    ),
    ("eds", "test_voltage", "low"): DiagnosisTemplate(
        "EDS 테스트 전압 하한 미달", "테스터 출력 저하 또는 프로브 접촉 불량",
        "불량 검출 민감도 저하(미검출 위험)",
        "프로브 카드 점검",
    ),
    ("eds", "test_current", "high"): DiagnosisTemplate(
        "EDS 테스트 전류 상한 초과", "다이 누설 전류 의심(실제 불량 가능성)",
        "불량(누설) 다이가 다음 공정으로 유출될 위험",
        "해당 다이 재검사, 웨이퍼 맵 클러스터링 확인",
    ),
    ("eds", "test_current", "low"): DiagnosisTemplate(
        "EDS 테스트 전류 하한 미달", "프로브 접촉 불량",
        "정상 다이를 불량으로 오판정(과검출) 위험",
        "프로브 카드 정렬 재확인",
    ),
    ("packaging", "dicing_speed", "high"): DiagnosisTemplate(
        "다이싱 속도 상한 초과", "장비 이송 속도 설정 오류",
        "다이 칩핑(chipping)/크랙 위험",
        "장비 파라미터 재확인, 블레이드 마모 점검",
    ),
    ("packaging", "dicing_speed", "low"): DiagnosisTemplate(
        "다이싱 속도 하한 미달", "블레이드 저항 증가(마모/이물질)",
        "처리량 저하, 블레이드 마모 가속",
        "블레이드 교체",
    ),
    ("packaging", "bonding_strength", "high"): DiagnosisTemplate(
        "본딩 강도 상한 초과", "본딩 압력/시간 과다",
        "다이 크랙 위험",
        "본딩 레시피 파라미터 하향 조정",
    ),
    ("packaging", "bonding_strength", "low"): DiagnosisTemplate(
        "본딩 강도 하한 미달", "본딩 압력/시간 부족 또는 표면 오염",
        "본딩 박리(delamination) 위험, 신뢰성 저하",
        "본딩 파라미터 상향, 표면 클리닝 점검",
    ),
    ("packaging", "temperature", "high"): DiagnosisTemplate(
        "본딩 온도 상한 초과", "본딩 스테이지 히터 오버슈트",
        "패키지 열손상 위험",
        "히터 컨트롤러 점검",
    ),
    ("packaging", "temperature", "low"): DiagnosisTemplate(
        "본딩 온도 하한 미달", "히터 예열 부족",
        "본딩 접착력 저하, 신뢰성 저하",
        "예열 시간 재설정",
    ),
}


def diagnose(process: str, params: dict[str, float]) -> list[Diagnosis]:
    """규격(low/high)을 벗어난 파라미터마다 진단을 하나씩 만든다. 전부 정상이면 빈 리스트."""
    if process not in PROCESS_SPECS:
        raise ValueError(f"Unknown process: {process}. Valid: {list(PROCESS_SPECS)}")

    results: list[Diagnosis] = []
    for spec in PROCESS_SPECS[process]:
        value = params.get(spec.name)
        if value is None:
            continue
        if value > spec.high:
            direction: Direction = "high"
        elif value < spec.low:
            direction = "low"
        else:
            continue

        template = DIAGNOSIS_TEMPLATES.get((process, spec.name, direction))
        if template is None:
            continue  # 매핑 누락 방어 — 테스트에서 24개 파라미터 x 2방향 전체 매핑 여부를 검증한다

        results.append(Diagnosis(
            process=process,
            parameter=spec.name,
            value=value,
            spec_low=spec.low,
            spec_high=spec.high,
            unit=spec.unit,
            direction=direction,
            label=template.label,
            cause=template.cause,
            impact=template.impact,
            action=template.action,
        ))
    return results
