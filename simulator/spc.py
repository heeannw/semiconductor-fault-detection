"""SPC(Statistical Process Control) 유틸리티 — I-MR 관리도, 공정능력지수, Western Electric 룰.

`simulator/process_simulator.py`가 정의한 실제 단위/규격(low, high)이 있는 공정 파라미터에
적용한다. SECOM은 피처가 익명화돼 있어(단위·규격 없음) 대상이 아니다 —
notebooks/10_spc_process_capability.ipynb 참고.
"""
from __future__ import annotations

import numpy as np

D2_N2 = 1.128  # 이동범위(n=2) 기반 시그마 추정 상수
D4_N2 = 3.267  # MR 관리도 UCL 상수


def i_mr_limits(values: np.ndarray) -> dict:
    """개별값(I) 관리도의 중심선/관리한계를 이동범위(MR)로 추정한다."""
    values = np.asarray(values, dtype=float)
    mean = values.mean()
    mr = np.abs(np.diff(values))
    mr_bar = mr.mean()
    sigma_short = mr_bar / D2_N2
    return {
        "center": float(mean),
        "sigma_short": float(sigma_short),
        "ucl": float(mean + 3 * sigma_short),
        "lcl": float(mean - 3 * sigma_short),
        "mr_bar": float(mr_bar),
        "mr_ucl": float(D4_N2 * mr_bar),
    }


def capability_indices(values: np.ndarray, low: float, high: float, sigma_short: float) -> dict:
    """Cp/Cpk(단기 변동 기준)와 Pp/Ppk(장기 변동 기준)를 계산한다."""
    values = np.asarray(values, dtype=float)
    mean = values.mean()
    sigma_long = values.std(ddof=1)
    cp = (high - low) / (6 * sigma_short)
    cpk = min((high - mean) / (3 * sigma_short), (mean - low) / (3 * sigma_short))
    pp = (high - low) / (6 * sigma_long)
    ppk = min((high - mean) / (3 * sigma_long), (mean - low) / (3 * sigma_long))
    return {
        "mean": float(mean),
        "sigma_short": float(sigma_short),
        "sigma_long": float(sigma_long),
        "Cp": float(cp),
        "Cpk": float(cpk),
        "Pp": float(pp),
        "Ppk": float(ppk),
    }


def capability_rating(cpk: float) -> str:
    if cpk >= 1.33:
        return "우수"
    if cpk >= 1.0:
        return "양호(관리 필요)"
    return "부적합"


def western_electric_flags(values: np.ndarray, center: float, sigma: float) -> np.ndarray:
    """Western Electric 4개 룰 중 하나라도 걸리면 그 지점을 이상(1)으로 표시한다.

    1) 3시그마 밖 한 점
    2) 연속 3개 중 2개가 같은 쪽 2시그마 밖
    3) 연속 5개 중 4개가 같은 쪽 1시그마 밖
    4) 연속 8개가 중심선 같은 쪽
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    z = (values - center) / sigma
    flags = np.zeros(n, dtype=bool)

    flags |= np.abs(z) > 3

    for i in range(2, n):
        window = z[i - 2:i + 1]
        if (window > 2).sum() >= 2 or (window < -2).sum() >= 2:
            flags[i] = True

    for i in range(4, n):
        window = z[i - 4:i + 1]
        if (window > 1).sum() >= 4 or (window < -1).sum() >= 4:
            flags[i] = True

    for i in range(7, n):
        window = z[i - 7:i + 1]
        if (window > 0).all() or (window < 0).all():
            flags[i] = True

    return flags.astype(int)
