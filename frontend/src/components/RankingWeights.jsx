const WEIGHTS = [
  { key: "alpha", label: "α semantic" },
  { key: "beta", label: "β recency" },
  { key: "gamma", label: "γ feedback" },
];

export default function RankingWeights({ history }) {
  const { current, weight_min, weight_max, learning_rate, snapshots } = history;
  return (
    <section className="card">
      <h2 className="headline-sm">Ranking weights</h2>
      <p className="body-sm muted">
        Current values after {snapshots.length - 1} updates, bounded to [{weight_min}, {weight_max}],
        learning rate {learning_rate}
      </p>
      {WEIGHTS.map(({ key, label }) => (
        <div className="weight" key={key}>
          <span>{label}</span>
          <div className="bar">
            <div style={{ width: `${current[key] * 100}%` }} />
          </div>
          <span>{current[key].toFixed(2)}</span>
        </div>
      ))}
    </section>
  );
}
