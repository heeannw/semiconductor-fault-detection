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
    </div>
  );
}
