export function RiskBars({
  items,
}: {
  items: Array<{
    risk_level: string;
    count: number;
  }>;
}) {
  const highest = Math.max(...items.map((item) => item.count), 1);
  return (
    <div className="panel">
      <div className="section-heading">
        <div>
          <div className="brand-kicker">Distribution</div>
          <h2>Risk Levels</h2>
        </div>
      </div>
      <div className="bar-stack">
        {items.map((item) => (
          <div className="line-item" key={item.risk_level}>
            <div className="line-meta">
              <span>{item.risk_level}</span>
              <span className="mono">{item.count}</span>
            </div>
            <div className="line-bar">
              <div
                className="line-fill"
                style={{
                  width: `${(item.count / highest) * 100}%`,
                  background:
                    item.risk_level === "low"
                      ? "linear-gradient(90deg, rgba(0,255,136,0.85), rgba(56,189,248,0.8))"
                      : item.risk_level === "medium"
                        ? "linear-gradient(90deg, rgba(56,189,248,0.85), rgba(250,204,21,0.8))"
                        : "linear-gradient(90deg, rgba(250,204,21,0.85), rgba(239,68,68,0.82))",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
