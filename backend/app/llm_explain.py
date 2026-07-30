"""Gemini API로 규칙 기반 진단 + AI 분류 결과를 자연어로 설명하는 얇은 레이어.

**중요한 설계 원칙**: Gemini가 새로운 판단을 내리게 하지 않는다. 원인 후보/영향/조치는
전부 `simulator/diagnosis.py`(규칙)와 `simulator/fault_classifier.py`(학습된 분류 모델)가
이미 결정론적으로 계산해 둔 사실이고, 여기서는 그 사실을 프롬프트에 그대로 박아 넣은 뒤
"이 사실에 근거해서만 답하라"고 지시한다 — RAG(검색 증강 생성)와 같은 구조다. 이렇게 하는
이유는, 반도체 공정 원인 진단처럼 틀리면 실제 피해로 이어질 수 있는 판단을 LLM의 환각에
맡기지 않기 위해서다. Gemini의 역할은 "판단"이 아니라 "이미 나온 판단을 자연스러운 문장으로
설명"하는 것으로 의도적으로 제한했다.

무료 등급(Gemini API 무료 티어) 기준으로 설계했다 — 사용자가 명시적으로 질문을 입력했을 때만
1회 호출하고, 자동으로 반복 호출하거나 재시도 루프를 돌리지 않는다.
"""
from __future__ import annotations

import os

from google import genai

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def gemini_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _format_diagnoses(diagnoses: list) -> str:
    if not diagnoses:
        return "(규칙 기반 진단 결과: 모든 파라미터가 규격 안에 있음)"
    lines = []
    for d in diagnoses:
        lines.append(
            f"- {d.label}: 측정값 {d.value}{d.unit} (규격 {d.spec_low}~{d.spec_high}{d.unit}), "
            f"원인 후보={d.cause}, 영향={d.impact}, 조치={d.action}"
        )
    return "\n".join(lines)


def _format_prediction(prediction) -> str:
    if prediction is None:
        return "(AI 분류 모델 예측 없음 — 모델 미학습)"
    probs = ", ".join(f"{label} {p:.0%}" for label, p in sorted(prediction.probabilities.items(), key=lambda x: -x[1]))
    return f"예측 원인: {prediction.predicted_label_ko} (확신도 {prediction.confidence:.0%})\n전체 확률 분포: {probs}"


def explain(
    process_name_ko: str,
    params: dict[str, float],
    diagnoses: list,
    prediction,
    question: str,
) -> str:
    """`GEMINI_API_KEY` 미설정 시 `RuntimeError`, Gemini 호출 자체가 실패하면 그 예외를
    그대로 올린다 — 호출부(`main.py`)가 각각 503/502로 변환한다."""
    if not gemini_available():
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
    prompt = f"""너는 반도체 fab 공정 엔지니어를 돕는 설명 도우미다. 아래에 이미 확정된 사실만 근거로
질문에 답하라 — 아래 나열되지 않은 새로운 원인이나 조치를 지어내지 마라. 모르면 "주어진 진단
결과만으로는 알 수 없다"고 답하라. 한국어로, 3~5문장 정도로 간결하게 답하라.

[공정] {process_name_ko}
[측정값] {params_str}

[규칙 기반 진단 결과]
{_format_diagnoses(diagnoses)}

[AI 분류 모델 예측]
{_format_prediction(prediction)}

[질문]
{question}
"""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text
