"""OHT 반송 이산사건 시뮬레이션 (SimPy).

FOUP(웨이퍼 로트)이 8개 공정 스테이션을 순서대로 통과하며, 스테이션 간 이동은
OHT 차량이 담당한다. 차량 배정(디스패칭) 정책을 바꿔가며 같은 시나리오를
비교할 수 있도록 정책을 함수로 분리했다.

단순화를 위해 디스패처는 "유휴 차량이 생겼는지"를 1초 간격으로 폴링한다.
실제 MCS는 이벤트 기반으로 즉시 반응하지만, 이 정도 규모(차량 수십 대 이하)의
시뮬레이션에서는 폴링 방식이 훨씬 읽기 쉽고 결과 차이도 무시할 수 있는 수준이다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
import simpy

from .layout import PICKUP_DROPOFF_SEC, STATION_ORDER, STATIONS, next_station, travel_time_seconds

DISPATCH_POLL_INTERVAL_SEC = 1.0


@dataclass
class Vehicle:
    id: int
    position: str
    busy: bool = False
    home_zone: int = 0
    busy_seconds: float = 0.0


@dataclass
class TransportRequest:
    foup_id: int
    from_station: str
    to_station: str
    created_at: float
    done_event: simpy.Event
    assigned_vehicle_id: int | None = None


def nearest_vehicle_dispatch(request: TransportRequest, idle_vehicles: list[Vehicle]) -> Vehicle:
    """유휴 차량 중 반송 요청 발생 지점(from_station)까지 가장 가까운 차량을 고른다."""
    return min(idle_vehicles, key=lambda v: travel_time_seconds(v.position, request.from_station))


def fcfs_dispatch(request: TransportRequest, idle_vehicles: list[Vehicle]) -> Vehicle:
    """위치와 무관하게 차량 ID가 가장 작은(먼저 등록된) 유휴 차량을 고른다 — 위치를 고려하지 않는 베이스라인."""
    return min(idle_vehicles, key=lambda v: v.id)


def make_zone_based_dispatch(n_zones: int = 2) -> Callable[[TransportRequest, list[Vehicle]], Vehicle]:
    """스테이션을 n_zones개 구역으로 나눠, 요청이 발생한 구역을 담당하는 차량을 우선 배정한다."""

    def zone_of(station: str) -> int:
        stations_per_zone = len(STATION_ORDER) / n_zones
        return int(STATIONS[station].index // stations_per_zone)

    def policy(request: TransportRequest, idle_vehicles: list[Vehicle]) -> Vehicle:
        req_zone = zone_of(request.from_station)
        same_zone = [v for v in idle_vehicles if v.home_zone == req_zone]
        pool = same_zone if same_zone else idle_vehicles
        return min(pool, key=lambda v: travel_time_seconds(v.position, request.from_station))

    return policy


zone_based_dispatch = make_zone_based_dispatch(n_zones=2)


def _foup_process(
    env: simpy.Environment,
    foup_id: int,
    station_resources: dict[str, simpy.Resource],
    request_queue: simpy.Store,
    rng: np.random.Generator,
    transport_log: list[dict],
    n_laps: int,
):
    station = STATION_ORDER[0]
    for lap in range(n_laps):
        for _ in range(len(STATION_ORDER)):
            spec = STATIONS[station]
            with station_resources[station].request() as req:
                yield req
                process_time = max(1.0, rng.normal(spec.process_time_mean_sec, spec.process_time_std_sec))
                yield env.timeout(process_time)

            destination = next_station(station)
            done_event = env.event()
            request = TransportRequest(
                foup_id=foup_id,
                from_station=station,
                to_station=destination,
                created_at=env.now,
                done_event=done_event,
            )
            yield request_queue.put(request)
            yield done_event

            transport_log.append({
                "foup_id": foup_id,
                "from": station,
                "to": destination,
                "requested_at": request.created_at,
                "completed_at": env.now,
                "cycle_time_sec": env.now - request.created_at,
                "vehicle_id": request.assigned_vehicle_id,
            })
            station = destination


def _dispatcher_process(
    env: simpy.Environment,
    request_queue: simpy.Store,
    vehicles: list[Vehicle],
    dispatch_policy: Callable[[TransportRequest, list[Vehicle]], Vehicle],
):
    while True:
        request = yield request_queue.get()
        while True:
            idle = [v for v in vehicles if not v.busy]
            if idle:
                break
            yield env.timeout(DISPATCH_POLL_INTERVAL_SEC)

        chosen = dispatch_policy(request, idle)
        chosen.busy = True
        request.assigned_vehicle_id = chosen.id
        env.process(_execute_transport(env, chosen, request))


def _execute_transport(env: simpy.Environment, vehicle: Vehicle, request: TransportRequest):
    start = env.now

    travel_to_pickup = travel_time_seconds(vehicle.position, request.from_station)
    yield env.timeout(travel_to_pickup + PICKUP_DROPOFF_SEC)

    travel_to_dropoff = travel_time_seconds(request.from_station, request.to_station)
    yield env.timeout(travel_to_dropoff + PICKUP_DROPOFF_SEC)

    vehicle.position = request.to_station
    vehicle.busy = False
    vehicle.busy_seconds += env.now - start

    request.done_event.succeed()


def run_simulation(
    n_vehicles: int = 5,
    n_foups: int = 20,
    n_laps: int = 3,
    dispatch_policy: Callable[[TransportRequest, list[Vehicle]], Vehicle] = nearest_vehicle_dispatch,
    foup_launch_interval_sec: float = 150.0,
    seed: int = 42,
) -> dict:
    """FOUP `n_foups`개가 각각 8개 스테이션 순환을 `n_laps`바퀴 도는 시나리오를 시뮬레이션한다."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    env = simpy.Environment()
    station_resources = {name: simpy.Resource(env, capacity=1) for name in STATION_ORDER}
    request_queue = simpy.Store(env)

    vehicles = [
        Vehicle(id=i, position=STATION_ORDER[i % len(STATION_ORDER)], home_zone=i % 2)
        for i in range(n_vehicles)
    ]

    transport_log: list[dict] = []

    def launch_foups():
        for foup_id in range(n_foups):
            env.process(_foup_process(env, foup_id, station_resources, request_queue, rng, transport_log, n_laps))
            yield env.timeout(rng.exponential(foup_launch_interval_sec))

    env.process(launch_foups())
    env.process(_dispatcher_process(env, request_queue, vehicles, dispatch_policy))

    # 정책 간 공정한 비교를 위해 넉넉한 시간 예산을 준다 — 혼잡이 심한(나쁜) 정책의 뒤쪽
    # FOUP들이 시간 초과로 잘려나가면, 그 느린 구간이 평균에서 빠져 오히려 좋아 보이는
    # 왜곡(우측 절단 편향)이 생긴다. 완료율은 아래 completion_rate로 항상 확인한다.
    total_launch_time = foup_launch_interval_sec * n_foups
    per_foup_time = len(STATION_ORDER) * n_laps * 1200.0
    env.run(until=total_launch_time + per_foup_time)

    log_df = pd.DataFrame(transport_log)
    sim_duration = env.now

    utilization = {
        f"vehicle_{v.id}": round(v.busy_seconds / sim_duration, 4) if sim_duration > 0 else 0.0
        for v in vehicles
    }

    return {
        "transport_log": log_df,
        "vehicle_utilization": utilization,
        "avg_vehicle_utilization": float(np.mean(list(utilization.values()))) if utilization else 0.0,
        "avg_cycle_time_sec": float(log_df["cycle_time_sec"].mean()) if len(log_df) else float("nan"),
        "p95_cycle_time_sec": float(log_df["cycle_time_sec"].quantile(0.95)) if len(log_df) else float("nan"),
        "completed_transports": len(log_df),
        "expected_transports": n_foups * n_laps * len(STATION_ORDER),
        "completion_rate": round(len(log_df) / (n_foups * n_laps * len(STATION_ORDER)), 4),
        "sim_duration_sec": sim_duration,
    }
