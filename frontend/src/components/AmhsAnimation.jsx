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

export default function AmhsAnimation({ stations, events }) {
  const canvasRef = useRef(null);
  const timeRef = useRef(0);
  const playingRef = useRef(true);
  const speedRef = useRef(1);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [scrub, setScrub] = useState(0);

  const sortedStations = useMemo(() => [...stations].sort((a, b) => a.index - b.index), [stations]);
  const indexOf = useMemo(() => Object.fromEntries(sortedStations.map((s) => [s.name, s.index])), [sortedStations]);
  const vehicleIds = useMemo(() => [...new Set(events.map((e) => e.vehicle_id))].sort((a, b) => a - b), [events]);
  const timelines = useMemo(() => buildVehicleTimelines(events), [events]);
  const maxTime = useMemo(
    () => (events.length ? Math.max(...events.map((e) => e.completed_at)) : 0),
    [events],
  );
  // 실제 시뮬레이션 시간(수백~수천 초)을 화면에서 약 25초 안팎으로 압축 재생한다.
  const baseCompression = useMemo(() => (maxTime > 0 ? maxTime / 25 : 1), [maxTime]);

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
      sortedStations.forEach((s) => {
        const angle = angleForIndex(s.index);
        const { x, y } = posForAngle(angle);

        ctx.save();
        ctx.shadowColor = "rgba(11, 11, 11, 0.18)";
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 2;
        ctx.beginPath();
        ctx.arc(x, y, STATION_R, 0, TWO_PI);
        ctx.fillStyle = colors.station;
        ctx.fill();
        ctx.restore();

        ctx.lineWidth = 2;
        ctx.strokeStyle = colors.stationBorder;
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
        ctx.font = "600 12px sans-serif";
        const textW = ctx.measureText(s.name_ko).width;
        const pillW = textW + 20;
        const pillH = 24;
        ctx.save();
        ctx.shadowColor = "rgba(11, 11, 11, 0.1)";
        ctx.shadowBlur = 4;
        ctx.fillStyle = colors.labelBg;
        roundRect(ctx, lx - pillW / 2, ly - pillH / 2, pillW, pillH, pillH / 2);
        ctx.fill();
        ctx.restore();
        ctx.lineWidth = 1;
        ctx.strokeStyle = colors.labelBorder;
        roundRect(ctx, lx - pillW / 2, ly - pillH / 2, pillW, pillH, pillH / 2);
        ctx.stroke();

        ctx.fillStyle = colors.text;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(s.name_ko, lx, ly);
      });

      // 차량: 진행 방향으로 옅어지는 잔상을 남겨 움직임을 강조하고, 그림자+흰 테두리로
      // 트랙/스테이션 위에서도 또렷하게 보이게 한다.
      vehicleIds.forEach((vid) => {
        const timeline = timelines.get(vid) || [];
        const { fromIndex, frac, isHotLot } = vehicleStateAt(timeline, vid, n, indexOf, t);
        const angle = angleForIndex(fromIndex) + frac * (TWO_PI / n);
        const color = isHotLot ? colors.hotLot : colors.vehicle;

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
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "700 10px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(vid), x, y);
      });

      const timeLabel = `${t.toFixed(0)}초 / ${maxTime.toFixed(0)}초`;
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
  }, [sortedStations, vehicleIds, timelines, indexOf, maxTime, baseCompression, events]);

  const handleScrub = (e) => {
    const value = Number(e.target.value);
    timeRef.current = value;
    setScrub(value);
    playingRef.current = false;
    setPlaying(false);
  };

  return (
    <div>
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
      </p>
    </div>
  );
}
