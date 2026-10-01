const LINKS = ["Research", "Papers", "Improvement history", "Experiments", "System"];

export default function Sidebar({ active }) {
  return (
    <aside className="sidebar">
      <div className="brand">Self-Improving RAG</div>
      <nav>
        {LINKS.map((label) => (
          <a key={label} href="#" className={label === active ? "active" : undefined}>
            {label}
          </a>
        ))}
      </nav>
    </aside>
  );
}
