"""OHT 반송 이산사건 시뮬레이션 (SimPy).

FOUP(웨이퍼 로트)이 8개 공정 스테이션을 순서대로 통과하며, 스테이션 간 이동은
OHT 차량이 담당한다. 차량 배정(디스패칭) 정책을 바꿔가며 같은 시나리오를
비교할 수 있도록 정책을 함수로 분리했다.

**스토커(입력 버퍼)와 back-pressure**: 각 스테이션 앞에는 용량이 제한된 스토커가 있다.
공정을 마친 FOUP은 다음 스테이션의 스토커에 자리가 없으면 그 자리에서 OHT에 실린 채
대기한다 — 이 동안 OHT도, 방금 공정을 마친 스테이션의 설비도 묶여 있다. 즉 다운스트림이
막히면 정체가 업스트림으로 번진다(back-pressure). `stocker_capacity=0`에 가깝게 두면
이 효과가 뚜렷해지고, 크게 두면 완충 효과로 거의 안 보인다.

단순화를 위해 디스패처는 "유휴 차량이 생겼는지"를 1초 간격으로 폴링한다.
실제 MCS는 이벤트 기반으로 즉시 반응하지만, 이 정도 규모(차량 수십 대 이하)의
시뮬레이션에서는 폴링 방식이 훨씬 읽기 쉽고 결과 차이도 무시할 수 있는 수준이다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import simpy

from .layout import PICKUP_DROPOFF_SEC, STATION_ORDER, STATIONS, next_station, travel_time_seconds

DISPATCH_POLL_INTERVAL_SEC = 1.0
DEFAULT_STOCKER_CAPACITY = 2
DEFAULT_CONGESTION_SAMPLE_INTERVAL_SEC = 60.0


@dataclass
class Vehicle:
    id: int
    position: str
    busy: bool = False
    home_zone: int = 0
    busy_seconds: float = 0.0
    under_maintenance: bool = False
    downtime_seconds: float = 0.0


@dataclass
class TransportRequest:
    foup_id: int
    from_station: str
    to_station: str
    created_at: float
    picked_up_event: simpy.Event
    done_event: simpy.Event
    assigned_vehicle_id: int | None = None


DispatchPolicy = Callable[["TransportRequest", list[Vehicle], list[Vehicle]], Vehicle]


def nearest_vehicle_dispatch(request: TransportRequest, idle_vehicles: list[Vehicle], all_vehicles: list[Vehicle] | None = None) -> Vehicle:
    """유휴 차량 중 반송 요청 발생 지점(from_station)까지 가장 가까운 차량을 고른다."""
    return min(idle_vehicles, key=lambda v: travel_time_seconds(v.position, request.from_station))


def fcfs_dispatch(request: TransportRequest, idle_vehicles: list[Vehicle], all_vehicles: list[Vehicle] | None = None) -> Vehicle:
    """위치와 무관하게 차량 ID가 가장 작은(먼저 등록된) 유휴 차량을 고른다 — 위치를 고려하지 않는 베이스라인."""
    return min(idle_vehicles, key=lambda v: v.id)


def make_zone_based_dispatch(n_zones: int = 2) -> DispatchPolicy:
    """스테이션을 n_zones개 구역으로 나눠, 요청이 발생한 구역을 담당하는 차량을 우선 배정한다."""

    def zone_of(station: str) -> int:
        stations_per_zone = len(STATION_ORDER) / n_zones
        return int(STATIONS[station].index // stations_per_zone)

    def policy(request: TransportRequest, idle_vehicles: list[Vehicle], all_vehicles: list[Vehicle] | None = None) -> Vehicle:
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
    input_stockers: dict[str, simpy.Store],
    request_queue: simpy.Store,
    rng: np.random.Generator,
    transport_log: list[dict],
    n_laps: int,
    wip_resource: simpy.Resource,
):
    # 순환 레이아웃 + 용량 제한 스토커는 WIP(동시 투입량)가 너무 많으면 서로 물려 교착상태에
    # 빠질 수 있다(모든 스토커가 꽉 차고 모든 설비가 픽업을 기다리는 상태) — 실제 fab에서
    # CONWIP(Constant WIP)로 투입량을 제한해 이를 막는 것과 같은 이유로, 여기서도 동시
    # 진행 중인 FOUP 수를 `wip_resource`로 제한한다.
    with wip_resource.request() as wip_req:
        yield wip_req
        yield from _foup_journey(env, foup_id, station_resources, input_stockers, request_queue, rng, transport_log, n_laps)


def _foup_journey(
    env: simpy.Environment,
    foup_id: int,
    station_resources: dict[str, simpy.Resource],
    input_stockers: dict[str, simpy.Store],
    request_queue: simpy.Store,
    rng: np.random.Generator,
    transport_log: list[dict],
    n_laps: int,
):
    station = STATION_ORDER[0]
    first_entry = True
    total_steps = n_laps * len(STATION_ORDER)
    for step in range(total_steps):
        if not first_entry:
            yield input_stockers[station].get()
        first_entry = False

        with station_resources[station].request() as req:
            yield req
            spec = STATIONS[station]
            process_time = max(1.0, rng.normal(spec.process_time_mean_sec, spec.process_time_std_sec))
            yield env.timeout(process_time)

            # 전체 여정의 마지막 스테이션(마지막 바퀴의 패키징)이면 fab을 빠져나가는 것이므로
            # 다음 스테이션으로의 반송을 만들지 않는다 — 그렇지 않으면 아무도 꺼내가지 않는
            # station 0 스토커에 영원히 자리를 차지하는 유령 반송이 생긴다.
            if step == total_steps - 1:
                break

            destination = next_station(station)
            picked_up_event = env.event()
            done_event = env.event()
            request = TransportRequest(
                foup_id=foup_id,
                from_station=station,
                to_station=destination,
                created_at=env.now,
                picked_up_event=picked_up_event,
                done_event=done_event,
            )
            yield request_queue.put(request)
            # OHT가 실제로 집어들 때까지 설비를 놓지 않는다 — 다음 FOUP을 못 받으므로
            # 이게 바로 back-pressure가 상류로 전파되는 지점이다.
            yield picked_up_event
        # `with` 블록 종료 -> 설비 자원 해제 (차량이 픽업한 시점에 이미 풀렸어야 함)

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
    input_stockers: dict[str, simpy.Store],
    dispatch_policy: DispatchPolicy,
):
    while True:
        request = yield request_queue.get()
        while True:
            idle = [v for v in vehicles if not v.busy and not v.under_maintenance]
            if idle:
                break
            yield env.timeout(DISPATCH_POLL_INTERVAL_SEC)

        chosen = dispatch_policy(request, idle, vehicles)
        chosen.busy = True
        request.assigned_vehicle_id = chosen.id
        env.process(_execute_transport(env, chosen, request, input_stockers))


def _execute_transport(
    env: simpy.Environment,
    vehicle: Vehicle,
    request: TransportRequest,
    input_stockers: dict[str, simpy.Store],
):
    start = env.now

    travel_to_pickup = travel_time_seconds(vehicle.position, request.from_station)
    yield env.timeout(travel_to_pickup + PICKUP_DROPOFF_SEC)
    request.picked_up_event.succeed()

    travel_to_dropoff = travel_time_seconds(request.from_station, request.to_station)
    yield env.timeout(travel_to_dropoff)

    # 목적지 스토커에 자리가 없으면 여기서 대기한다 — 차량이 묶여 있는 채로 back-pressure가 걸린다.
    yield input_stockers[request.to_station].put(request.foup_id)
    yield env.timeout(PICKUP_DROPOFF_SEC)

    vehicle.position = request.to_station
    vehicle.busy = False
    vehicle.busy_seconds += env.now - start

    request.done_event.succeed()


def _congestion_sampler(
    env: simpy.Environment,
    input_stockers: dict[str, simpy.Store],
    vehicles: list[Vehicle],
    congestion_log: list[dict],
    interval_sec: float,
):
    while True:
        busy_vehicles = sum(1 for v in vehicles if v.busy)
        under_maintenance = sum(1 for v in vehicles if v.under_maintenance)
        for station, stocker in input_stockers.items():
            congestion_log.append({
                "time": env.now,
                "station": station,
                "queue_length": len(stocker.items),
                "stocker_capacity": stocker.capacity,
                "busy_vehicles": busy_vehicles,
                "under_maintenance_vehicles": under_maintenance,
            })
        yield env.timeout(interval_sec)


def run_simulation(
    n_vehicles: int = 5,
    n_foups: int = 20,
    n_laps: int = 3,
    dispatch_policy: DispatchPolicy = nearest_vehicle_dispatch,
    foup_launch_interval_sec: float = 150.0,
    stocker_capacity: int = DEFAULT_STOCKER_CAPACITY,
    max_wip: int | None = None,
    congestion_sample_interval_sec: float = DEFAULT_CONGESTION_SAMPLE_INTERVAL_SEC,
    maintenance_process: Callable | None = None,
    seed: int = 42,
) -> dict:
    """FOUP `n_foups`개가 각각 8개 스테이션 순환을 `n_laps`바퀴 도는 시나리오를 시뮬레이션한다.

    `max_wip`: 동시에 시스템 안에 있을 수 있는 FOUP 수 상한(CONWIP). `None`이면
    `len(STATION_ORDER) * stocker_capacity`(전체 스토커 용량)로 자동 설정 — 순환 레이아웃에서
    스토커가 다 차서 교착상태에 빠지는 것을 막는 안전장치다.
    `maintenance_process`: `(env, vehicles, rng) -> Generator`를 넘기면 추가 SimPy 프로세스로
    등록된다 — 예지보전 피드백(주기적으로 차량 상태를 점검해 이상 시 운행 중단)을 여기에 꽂는다.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    if max_wip is None:
        max_wip = max(1, len(STATION_ORDER) * stocker_capacity)

    env = simpy.Environment()
    station_resources = {name: simpy.Resource(env, capacity=1) for name in STATION_ORDER}
    input_stockers = {name: simpy.Store(env, capacity=stocker_capacity) for name in STATION_ORDER}
    request_queue = simpy.Store(env)
    wip_resource = simpy.Resource(env, capacity=max_wip)

    vehicles = [
        Vehicle(id=i, position=STATION_ORDER[i % len(STATION_ORDER)], home_zone=i % 2)
        for i in range(n_vehicles)
    ]

    transport_log: list[dict] = []
    congestion_log: list[dict] = []

    def launch_foups():
        for foup_id in range(n_foups):
            env.process(_foup_process(env, foup_id, station_resources, input_stockers, request_queue, rng, transport_log, n_laps, wip_resource))
            yield env.timeout(rng.exponential(foup_launch_interval_sec))

    env.process(launch_foups())
    env.process(_dispatcher_process(env, request_queue, vehicles, input_stockers, dispatch_policy))
    env.process(_congestion_sampler(env, input_stockers, vehicles, congestion_log, congestion_sample_interval_sec))
    if maintenance_process is not None:
        env.process(maintenance_process(env, vehicles, rng))

    # 정책 간 공정한 비교를 위해 넉넉한 시간 예산을 준다 — 혼잡이 심한(나쁜) 정책의 뒤쪽
    # FOUP들이 시간 초과로 잘려나가면, 그 느린 구간이 평균에서 빠져 오히려 좋아 보이는
    # 왜곡(우측 절단 편향)이 생긴다. 완료율은 아래 completion_rate로 항상 확인한다.
    total_launch_time = foup_launch_interval_sec * n_foups
    per_foup_time = len(STATION_ORDER) * n_laps * 3000.0
    env.run(until=total_launch_time + per_foup_time)

    log_df = pd.DataFrame(transport_log)
    congestion_df = pd.DataFrame(congestion_log)
    sim_duration = env.now

    utilization = {
        f"vehicle_{v.id}": round(v.busy_seconds / sim_duration, 4) if sim_duration > 0 else 0.0
        for v in vehicles
    }
    downtime = {
        f"vehicle_{v.id}": round(v.downtime_seconds, 1)
        for v in vehicles
    }

    return {
        "transport_log": log_df,
        "congestion_log": congestion_df,
        "vehicle_utilization": utilization,
        "vehicle_downtime_sec": downtime,
        "avg_vehicle_utilization": float(np.mean(list(utilization.values()))) if utilization else 0.0,
        "avg_cycle_time_sec": float(log_df["cycle_time_sec"].mean()) if len(log_df) else float("nan"),
        "p95_cycle_time_sec": float(log_df["cycle_time_sec"].quantile(0.95)) if len(log_df) else float("nan"),
        "max_queue_length": int(congestion_df["queue_length"].max()) if len(congestion_df) else 0,
        "completed_transports": len(log_df),
        "expected_transports": n_foups * (n_laps * len(STATION_ORDER) - 1),
        "completion_rate": round(len(log_df) / (n_foups * (n_laps * len(STATION_ORDER) - 1)), 4),
        "sim_duration_sec": sim_duration,
    }
