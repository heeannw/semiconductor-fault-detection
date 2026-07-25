export default function StatTile({ label, value }) {
  return (
    <div className="card stat-tile">
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}
