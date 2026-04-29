type Point = {
  label: string;
  value: number;
  secondary: number;
};

export function LineChart({ title, points }: { title: string; points: Point[] }) {
  return (
    <div className="panel">
      <div className="section-heading">
        <div>
          <div className="brand-kicker">Trend</div>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="chart-lines">
        {points.map((point) => (
          <div className="line-item" key={point.label}>
            <div className="line-meta">
              <span>{point.label}</span>
              <span className="mono">
                {Math.round(point.value * 100)}% confidence · {Math.round(point.secondary * 100)}% risk
              </span>
            </div>
            <div className="line-bar">
              <div className="line-fill" style={{ width: `${Math.max(point.value, 0.03) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
