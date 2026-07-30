const PARAM_UNITS = {
  temperature: "°C",
  oxygen_concentration: "ppb",
  resistivity: "Ω·cm",
  time: "min",
  oxide_thickness: "nm",
  exposure_energy: "mJ/cm²",
  focus_distance: "μm",
  pressure: "mTorr",
  gas_flow: "sccm",
  power: "W",
  deposition_rate: "nm/min",
  current_density: "mA/cm²",
  plating_time: "min",
  test_voltage: "V",
  test_current: "μA",
  dicing_speed: "mm/s",
  bonding_strength: "g",
};

export default function ProcessCard({ log }) {
  return (
    <div className={`process-card${log.is_anomaly ? " is-anomaly" : ""}`}>
      <div className="process-title">
        <span>{log.process_name_ko}</span>
        <span className={`badge ${log.is_anomaly ? "badge-critical" : "badge-good"}`}>
          {log.is_anomaly ? "이상" : "정상"}
        </span>
      </div>
      {Object.entries(log.params).map(([key, value]) => (
        <div className="param-row" key={key}>
          <span className="param-name">{key}</span>
          <span>
            {value} {PARAM_UNITS[key] ?? ""}
          </span>
        </div>
      ))}
      {log.diagnoses?.length > 0 && (
        <div className="diagnosis-block">
          {log.diagnoses.map((d) => (
            <div className="diagnosis-item" key={d.parameter}>
              <div className="diagnosis-label">
                {d.label} ({d.direction === "high" ? "↑ 상한 초과" : "↓ 하한 미달"}: {d.value} {d.unit}, 규격 {d.spec_low}~{d.spec_high}{d.unit})
              </div>
              <div className="diagnosis-row"><span>원인 후보</span>{d.cause}</div>
              <div className="diagnosis-row"><span>영향</span>{d.impact}</div>
              <div className="diagnosis-row"><span>조치 제안</span>{d.action}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
