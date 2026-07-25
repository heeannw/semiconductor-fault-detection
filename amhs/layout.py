"""AMHS 반송 네트워크 레이아웃.

기존 `simulator/`의 8대 공정을 순환 레이아웃의 노드로 재사용한다(웨이퍼 제조 -> ... -> 패키징 -> 웨이퍼 제조).
실제 fab의 반송 경로는 제품별로 훨씬 복잡하지만(bay 간 이동, 재작업 루프 등),
디스패칭 정책의 효과를 비교하는 데는 이 정도의 단순화로 충분하다.
"""
from dataclasses import dataclass

from simulator import PROCESS_NAMES_KO, PROCESS_SPECS

STATION_ORDER: list[str] = list(PROCESS_SPECS)

SEGMENT_DISTANCE_M = 120.0  # 인접 스테이션 사이 구간 거리(단순화: 전 구간 동일)
OHT_SPEED_MPS = 3.3  # 실제 OHT 평균 주행속도(약 200m/min)에 근접한 값
PICKUP_DROPOFF_SEC = 8.0  # FOUP 집기/내려놓기 소요 시간


@dataclass(frozen=True)
class Station:
    name: str
    name_ko: str
    index: int
    process_time_mean_sec: float
    process_time_std_sec: float


STATIONS: dict[str, Station] = {
    name: Station(
        name=name,
        name_ko=PROCESS_NAMES_KO[name],
        index=i,
        process_time_mean_sec=180.0 + i * 15.0,
        process_time_std_sec=20.0,
    )
    for i, name in enumerate(STATION_ORDER)
}


def next_station(name: str) -> str:
    idx = STATIONS[name].index
    return STATION_ORDER[(idx + 1) % len(STATION_ORDER)]


def _forward_hops(a: str, b: str) -> int:
    n = len(STATION_ORDER)
    return (STATIONS[b].index - STATIONS[a].index) % n


def distance_between(a: str, b: str) -> float:
    return _forward_hops(a, b) * SEGMENT_DISTANCE_M


def travel_time_seconds(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return distance_between(a, b) / OHT_SPEED_MPS
