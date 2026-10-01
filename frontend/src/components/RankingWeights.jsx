const WEIGHTS = [
  { key: "alpha_init", label: "α semantic" },
  { key: "beta_init", label: "β recency" },
  { key: "gamma_init", label: "γ feedback" },
];

export default function RankingWeights({ ranking }) {
  return (
    <section className="card">
      <h2 className="headline-sm">Ranking weights</h2>
      <p className="body-sm muted">
        Initial values, bounded to [{ranking.weight_min}, {ranking.weight_max}], learning rate{" "}
        {ranking.learning_rate}
      </p>
      {WEIGHTS.map(({ key, label }) => (
        <div className="weight" key={key}>
          <span>{label}</span>
          <div className="bar">
            <div style={{ width: `${ranking[key] * 100}%` }} />
          </div>
          <span>{ranking[key].toFixed(2)}</span>
        </div>
      ))}
    </section>
  );
}
