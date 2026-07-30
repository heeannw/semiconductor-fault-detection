import { useEffect, useMemo, useRef, useState } from "react";

const TWO_PI = Math.PI * 2;
const SPEEDS = [0.5, 1, 2, 4];

// 시뮬레이션 시작 시 차량 초기 배치는 amhs/simulation.py의
// `Vehicle(position=STATION_ORDER[i % len(STATION_ORDER)])`와 동일한 규칙을 그대로 따른다 —
// 근사가 아니라 백엔드 로직을 그대로 옮긴 것이므로 첫 반송 이벤트 전에도 차량 위치가 정확하다.
// 같은 차량은 한 번에 한 건만 반송하므로(dispatcher가 idle 차량에게만 배정), completed_at
// 기준 정렬이 실제 실행 순서를 정확히 반영한다 — requested_at(요청 생성 시각)은 hot lot
// 우선순위 때문에 실행 순서와 어긋날 수 있어 정렬 키로 쓰지 않는다.
function buildVehicleTimelines(events) {
  const byVehicle = new Map();
  for (const ev of events) {
    if (!byVehicle.has(ev.vehicle_id)) byVehicle.set(ev.vehicle_id, []);
    byVehicle.get(ev.vehicle_id).push(ev);
  }
  for (const list of byVehicle.values()) list.sort((a, b) => a.completed_at - b.completed_at);
  return byVehicle;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function vehicleStateAt(timeline, vehicleId, nStations, indexOf, t) {
  let active = null;
  let lastCompleted = null;
  for (const ev of timeline) {
    if (ev.requested_at <= t && t <= ev.completed_at) { active = ev; break; }
    if (ev.completed_at <= t) lastCompleted = ev;
  }
  if (active) {
    const span = Math.max(active.completed_at - active.requested_at, 0.001);
    const frac = Math.min(Math.max((t - active.requested_at) / span, 0), 1);
    return { fromIndex: indexOf[active.from_station], frac, isHotLot: active.is_hot_lot };
  }
  if (lastCompleted) {
    return { fromIndex: indexOf[lastCompleted.to_station], frac: 0, isHotLot: false };
  }
  return { fromIndex: vehicleId % nStations, frac: 0, isHotLot: false };
}

// `amhs/simulation.py`의 `_congestion_sampler`가 일정 간격으로 스테이션별 대기열 길이를
// 남긴 기록 — station별로 시각순 정렬해두면, 재생 시각 t 이하 중 가장 최근 샘플을 찾아
// "지금 이 스테이션이 정체 중인지"를 그대로 재현할 수 있다.
function buildStationCongestionTimelines(congestion) {
  const byStation = new Map();
  for (const c of congestion) {
    if (!byStation.has(c.station)) byStation.set(c.station, []);
    byStation.get(c.station).push(c);
  }
  for (const list of byStation.values()) list.sort((a, b) => a.time - b.time);
  return byStation;
}

function congestionAt(timeline, t) {
  let last = null;
  for (const c of timeline) {
    if (c.time > t) break;
    last = c;
  }
  return last;
}

// `amhs/maintenance.py`가 남기는 {time, vehicle_id, event: "down"|"restored"} 기록 —
// 차량별로 정렬해두고, 재생 시각 t 이하 중 가장 최근 이벤트가 "down"이면 그 차량은
// 지금 예지보전으로 운행이 중단된 상태다.
function buildVehicleMaintenanceTimelines(maintenanceEvents) {
  const byVehicle = new Map();
  for (const e of maintenanceEvents) {
    if (!byVehicle.has(e.vehicle_id)) byVehicle.set(e.vehicle_id, []);
    byVehicle.get(e.vehicle_id).push(e);
  }
  for (const list of byVehicle.values()) list.sort((a, b) => a.time - b.time);
  return byVehicle;
}

function isDownAt(timeline, t) {
  let down = false;
  for (const e of timeline) {
    if (e.time > t) break;
    down = e.event === "down";
  }
  return down;
}

function isMovingAt(timeline, t) {
  return timeline.some((ev) => ev.requested_at <= t && t <= ev.completed_at);
}

// 좌측 차량 현황 패널의 "가동률" — t 시점까지 이 차량이 반송 중이었던 시간의 비율.
function utilizationAt(timeline, t) {
  if (t <= 0) return 0;
  let busy = 0;
  for (const ev of timeline) {
    if (ev.requested_at > t) continue;
    busy += Math.min(ev.completed_at, t) - ev.requested_at;
  }
  return Math.min(100, Math.round((busy / t) * 100));
}

const FLEET_STATE_BADGE_CLASS = {
  down: "badge-critical",
  hotlot: "badge-warning",
  moving: "badge-good",
  idle: "badge-muted",
};

export default function AmhsAnimation({ stations, events, congestion = [], maintenanceEvents = [], stockerCapacity = 2 }) {
  const canvasRef = useRef(null);
  const timeRef = useRef(0);
  const playingRef = useRef(true);
  const speedRef = useRef(1);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [scrub, setScrub] = useState(0);

  const sortedStations = useMemo(() => [...stations].sort((a, b) => a.index - b.index), [stations]);
  const indexOf = useMemo(() => Object.fromEntries(sortedStations.map((s) => [s.name, s.index])), [sortedStations]);
  const vehicleIds = useMemo(
    () => [...new Set([...events.map((e) => e.vehicle_id), ...maintenanceEvents.map((e) => e.vehicle_id)])].sort((a, b) => a - b),
    [events, maintenanceEvents],
  );
  const timelines = useMemo(() => buildVehicleTimelines(events), [events]);
  const congestionTimelines = useMemo(() => buildStationCongestionTimelines(congestion), [congestion]);
  const maintenanceTimelines = useMemo(() => buildVehicleMaintenanceTimelines(maintenanceEvents), [maintenanceEvents]);
  // 차량 고장(예지보전) 이벤트는 마지막 반송이 끝난 뒤에 발생할 수도 있으므로, 반송
  // 이벤트만으로 재생 구간을 정하면 그 고장 구간이 스크럽 범위 밖으로 잘려나가 절대
  // 재생되지 않는다 — maintenanceEvents의 시각도 함께 고려해 재생 구간을 정한다.
  const maxTime = useMemo(() => {
    const times = [...events.map((e) => e.completed_at), ...maintenanceEvents.map((e) => e.time)];
    return times.length ? Math.max(...times) : 0;
  }, [events, maintenanceEvents]);
  // 실제 시뮬레이션 시간(수백~수천 초)을 화면에서 약 25초 안팎으로 압축 재생한다.
  const baseCompression = useMemo(() => (maxTime > 0 ? maxTime / 25 : 1), [maxTime]);

  // 좌측 차량 현황 패널 — scrub은 재생 중 매 프레임 갱신되므로, 캔버스와 동일한 실시간성으로
  // 목록의 상태 배지/가동률도 함께 갱신된다.
  const vehicleStatuses = useMemo(() => {
    return vehicleIds.map((vid) => {
      const timeline = timelines.get(vid) || [];
      const down = isDownAt(maintenanceTimelines.get(vid) || [], scrub);
      const moving = !down && isMovingAt(timeline, scrub);
      const { isHotLot } = vehicleStateAt(timeline, vid, sortedStations.length || 1, indexOf, scrub);
      const utilization = utilizationAt(timeline, scrub);
      let state = "idle";
      let label = "대기 중";
      if (down) {
        state = "down";
        label = "고장 · 예지보전";
      } else if (moving && isHotLot) {
        state = "hotlot";
        label = "이동 중 · Hot Lot";
      } else if (moving) {
        state = "moving";
        label = "이동 중";
      }
      return { id: vid, state, label, utilization };
    });
  }, [vehicleIds, timelines, maintenanceTimelines, indexOf, sortedStations, scrub]);

  useEffect(() => {
    timeRef.current = 0;
    setScrub(0);
    playingRef.current = true;
    setPlaying(true);
  }, [events]);

  useEffect(() => { playingRef.current = playing; }, [playing]);
  useEffect(() => { speedRef.current = speed; }, [speed]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || sortedStations.length === 0) return undefined;
    const ctx = canvas.getContext("2d");
    if (!ctx) return undefined; // jsdom(테스트 환경) 등 canvas 2D 컨텍스트를 지원하지 않는 환경 방어

    // 마운트 직후엔 주변 레이아웃(그리드/카드 너비)이 아직 확정되지 않은 상태라
    // canvas.clientWidth를 한 번만 재서 내부 해상도를 고정하면 실제 표시 너비와 어긋나
    // 그림이 가로로 늘어나 보인다 — ResizeObserver로 실제 표시 크기가 바뀔 때마다 다시 잰다.
    const size = { width: canvas.clientWidth || 560, height: 460 };
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      size.width = canvas.clientWidth || 560;
      size.height = 460;
      canvas.width = size.width * dpr;
      canvas.height = size.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    const style = getComputedStyle(canvas);
    const colors = {
      track: style.getPropertyValue("--gridline").trim() || "#e1e0d9",
      trackLine: style.getPropertyValue("--baseline").trim() || "#c3c2b7",
      station: style.getPropertyValue("--surface-2").trim() || "#fff",
      stationBorder: style.getPropertyValue("--baseline").trim() || "#c3c2b7",
      stationIndex: style.getPropertyValue("--text-muted").trim() || "#898781",
      labelBg: style.getPropertyValue("--surface-1").trim() || "#fcfcfb",
      labelBorder: style.getPropertyValue("--border").trim() || "rgba(11,11,11,0.1)",
      text: style.getPropertyValue("--text-secondary").trim() || "#52514e",
      muted: style.getPropertyValue("--text-muted").trim() || "#898781",
      vehicle: style.getPropertyValue("--series-1").trim() || "#2a78d6",
      hotLot: style.getPropertyValue("--series-2").trim() || "#eb6834",
      vehicleRing: style.getPropertyValue("--surface-2").trim() || "#fff",
      congested: style.getPropertyValue("--status-critical").trim() || "#d33",
      down: style.getPropertyValue("--status-critical").trim() || "#d33",
    };

    const n = sortedStations.length;
    const angleForIndex = (i) => -Math.PI / 2 + i * (TWO_PI / n);

    let rafId;
    let lastTs = null;

    const STATION_R = 21;
    const VEHICLE_R = 11;

    const draw = (t) => {
      const { width: cssWidth, height: cssHeight } = size;
      const cx = cssWidth / 2;
      const cy = cssHeight / 2 - 6;
      const R = Math.min(cx, cy) - 82;
      const posForAngle = (angle) => ({ x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) });

      ctx.clearRect(0, 0, cssWidth, cssHeight);

      // 트랙: 얇은 선 대신 폭이 있는 "도로" + 중앙 점선으로 실제 반송 레일 느낌을 준다.
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, TWO_PI);
      ctx.lineWidth = 14;
      ctx.strokeStyle = colors.track;
      ctx.stroke();

      ctx.beginPath();
      ctx.setLineDash([3, 7]);
      ctx.arc(cx, cy, R, 0, TWO_PI);
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = colors.trackLine;
      ctx.stroke();
      ctx.setLineDash([]);

      // 스테이션: 그림자 있는 원 + 순번 + 라벨은 알약(pill) 배경 위에 올려 가독성을 높인다.
      // 정체 중(대기열 길이 >= 스토커 용량)인 스테이션은 테두리/라벨을 빨간색으로 강조해
      // "지금 여기서 병목이 발생하고 있다"는 것을 한눈에 알 수 있게 한다.
      sortedStations.forEach((s) => {
        const angle = angleForIndex(s.index);
        const { x, y } = posForAngle(angle);
        const sample = congestionAt(congestionTimelines.get(s.name) || [], t);
        const congested = !!sample && sample.queue_length >= stockerCapacity;

        ctx.save();
        ctx.shadowColor = "rgba(11, 11, 11, 0.18)";
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 2;
        ctx.beginPath();
        ctx.arc(x, y, STATION_R, 0, TWO_PI);
        ctx.fillStyle = colors.station;
        ctx.fill();
        ctx.restore();

        if (congested) {
          ctx.beginPath();
          ctx.arc(x, y, STATION_R + 5, 0, TWO_PI);
          ctx.lineWidth = 3;
          ctx.strokeStyle = colors.congested;
          ctx.globalAlpha = 0.45;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        ctx.lineWidth = congested ? 3 : 2;
        ctx.strokeStyle = congested ? colors.congested : colors.stationBorder;
        ctx.beginPath();
        ctx.arc(x, y, STATION_R, 0, TWO_PI);
        ctx.stroke();

        ctx.fillStyle = colors.stationIndex;
        ctx.font = "600 12px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(s.index + 1), x, y);

        const labelR = R + STATION_R + 30;
        const lx = cx + Math.cos(angle) * labelR;
        const ly = cy + Math.sin(angle) * labelR;
        const labelText = congested ? `${s.name_ko} · 정체 (대기 ${sample.queue_length})` : s.name_ko;
        ctx.font = "600 12px sans-serif";
        const textW = ctx.measureText(labelText).width;
        const pillW = textW + 20;
        const pillH = 24;
        ctx.save();
        ctx.shadowColor = "rgba(11, 11, 11, 0.1)";
        ctx.shadowBlur = 4;
        ctx.fillStyle = colors.labelBg;
        roundRect(ctx, lx - pillW / 2, ly - pillH / 2, pillW, pillH, pillH / 2);
        ctx.fill();
        ctx.restore();
        ctx.lineWidth = congested ? 2 : 1;
        ctx.strokeStyle = congested ? colors.congested : colors.labelBorder;
        roundRect(ctx, lx - pillW / 2, ly - pillH / 2, pillW, pillH, pillH / 2);
        ctx.stroke();

        ctx.fillStyle = congested ? colors.congested : colors.text;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(labelText, lx, ly);
      });

      // 차량: 진행 방향으로 옅어지는 잔상을 남겨 움직임을 강조하고, 그림자+흰 테두리로
      // 트랙/스테이션 위에서도 또렷하게 보이게 한다. 예지보전으로 운행 중단된(고장) 차량은
      // 멈춰선 상태이므로 잔상 없이 빨간 점선 테두리 + "고장" 라벨로 명확히 구분한다.
      vehicleIds.forEach((vid) => {
        const timeline = timelines.get(vid) || [];
        const { fromIndex, frac, isHotLot } = vehicleStateAt(timeline, vid, n, indexOf, t);
        const down = isDownAt(maintenanceTimelines.get(vid) || [], t);
        const angle = angleForIndex(fromIndex) + frac * (TWO_PI / n);
        const color = down ? colors.down : (isHotLot ? colors.hotLot : colors.vehicle);

        if (!down) {
          for (let i = 3; i >= 1; i--) {
            const trailFrac = Math.max(0, frac - i * 0.018);
            const trailAngle = angleForIndex(fromIndex) + trailFrac * (TWO_PI / n);
            const tp = posForAngle(trailAngle);
            ctx.beginPath();
            ctx.arc(tp.x, tp.y, VEHICLE_R - i * 2, 0, TWO_PI);
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.12 * (4 - i);
            ctx.fill();
          }
          ctx.globalAlpha = 1;
        }

        const { x, y } = posForAngle(angle);
        ctx.save();
        ctx.shadowColor = "rgba(11, 11, 11, 0.3)";
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(x, y, VEHICLE_R, 0, TWO_PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.restore();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = colors.vehicleRing;
        if (down) ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = "#ffffff";
        ctx.font = "700 10px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(vid), x, y);

        if (down) {
          const label = "고장";
          ctx.font = "700 10px sans-serif";
          const labelW = ctx.measureText(label).width;
          const pillW = labelW + 14;
          const pillH = 18;
          const px = x;
          const py = y - VEHICLE_R - 14;
          ctx.save();
          ctx.shadowColor = "rgba(11, 11, 11, 0.2)";
          ctx.shadowBlur = 3;
          ctx.fillStyle = colors.down;
          roundRect(ctx, px - pillW / 2, py - pillH / 2, pillW, pillH, pillH / 2);
          ctx.fill();
          ctx.restore();
          ctx.fillStyle = "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(label, px, py);
        }
      });

      const timeLabel = `시뮬레이션 ${t.toFixed(0)}초 / ${maxTime.toFixed(0)}초`;
      ctx.font = "600 11px sans-serif";
      const timeLabelW = ctx.measureText(timeLabel).width;
      ctx.fillStyle = colors.labelBg;
      roundRect(ctx, 8, cssHeight - 30, timeLabelW + 16, 22, 11);
      ctx.fill();
      ctx.strokeStyle = colors.labelBorder;
      ctx.lineWidth = 1;
      roundRect(ctx, 8, cssHeight - 30, timeLabelW + 16, 22, 11);
      ctx.stroke();
      ctx.fillStyle = colors.muted;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(timeLabel, 16, cssHeight - 19);
    };

    const tick = (ts) => {
      if (lastTs === null) lastTs = ts;
      const dtReal = (ts - lastTs) / 1000;
      lastTs = ts;
      if (playingRef.current && maxTime > 0) {
        const next = timeRef.current + dtReal * baseCompression * speedRef.current;
        timeRef.current = next >= maxTime ? maxTime : next;
        if (timeRef.current >= maxTime) playingRef.current = false;
        setScrub(timeRef.current);
      }
      draw(timeRef.current);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
    };
  }, [sortedStations, vehicleIds, timelines, congestionTimelines, maintenanceTimelines, stockerCapacity, indexOf, maxTime, baseCompression, events]);

  const handleScrub = (e) => {
    const value = Number(e.target.value);
    timeRef.current = value;
    setScrub(value);
    playingRef.current = false;
    setPlaying(false);
  };

  return (
    <div className="amhs-fleet-layout">
      <div className="amhs-fleet-list">
        <div className="amhs-fleet-list-header">차량 현황 ({vehicleStatuses.length}대)</div>
        {vehicleStatuses.length === 0 ? (
          <div className="empty-state">차량 데이터가 없습니다.</div>
        ) : (
          vehicleStatuses.map((v) => (
            <div className="amhs-fleet-item" key={v.id}>
              <span className={`amhs-fleet-dot amhs-fleet-dot-${v.state}`} />
              <div className="amhs-fleet-item-body">
                <div className="amhs-fleet-item-top">
                  <span className="amhs-fleet-item-id">AGV #{v.id}</span>
                  <span className={`badge ${FLEET_STATE_BADGE_CLASS[v.state]}`}>{v.label}</span>
                </div>
                <div className="amhs-fleet-bar-track">
                  <div className="amhs-fleet-bar-fill" style={{ width: `${v.utilization}%` }} />
                </div>
                <div className="amhs-fleet-item-meta">가동률 {v.utilization}%</div>
              </div>
            </div>
          ))
        )}
      </div>
      <div className="amhs-fleet-canvas">
        <canvas
          ref={canvasRef}
          style={{ width: "100%", height: 460, display: "block" }}
          role="img"
          aria-label="OHT 반송 애니메이션"
        />
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button onClick={() => setPlaying((p) => !p)}>{playing ? "일시정지" : "재생"}</button>
          {SPEEDS.map((s) => (
            <button
              key={s}
              className={s === speed ? undefined : "secondary"}
              onClick={() => setSpeed(s)}
            >
              {s}x
            </button>
          ))}
          <input
            type="range"
            min="0"
            max={maxTime || 1}
            step="1"
            value={scrub}
            onChange={handleScrub}
            style={{ flex: 1, minWidth: 120 }}
          />
        </div>
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
          원은 8개 공정 스테이션, 점은 OHT 차량(번호는 vehicle_id). 주황색 점은 Hot Lot을 나르는 중인 차량.
          빨간 테두리 스테이션은 대기열이 스토커 용량을 넘은 정체 상태, 빨간 점선 테두리 + "고장" 표시 차량은 예지보전으로 운행이 중단된 차량.
        </p>
      </div>
    </div>
  );
}
