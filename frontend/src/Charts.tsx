export function LineChart({
  points,
  title,
  xLabel,
  yLabel,
  diagonal = false,
  color = '#55d6be',
}: {
  points: number[][];
  title: string;
  xLabel: string;
  yLabel: string;
  diagonal?: boolean;
  color?: string;
}) {
  const x = (n: number) => 50 + n * 380,
    y = (n: number) => 220 - n * 185;
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox="0 0 460 260" role="img" aria-label={title}>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1="50" y1={y(t)} x2="430" y2={y(t)} stroke="#273448" />
            <text x="40" y={y(t) + 4} textAnchor="end">
              {t.toFixed(2)}
            </text>
            <text x={x(t)} y="239" textAnchor="middle">
              {t.toFixed(2)}
            </text>
          </g>
        ))}
        {diagonal && (
          <line x1={x(0)} x2={x(1)} y1={y(0)} y2={y(1)} stroke="#8291a8" strokeDasharray="5 5" />
        )}
        <polyline
          points={points.map((p) => `${x(p[0])},${y(p[1])}`).join(' ')}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
        />
        {points.map((p, i) => (
          <circle key={i} cx={x(p[0])} cy={y(p[1])} r={points.length < 20 ? 4 : 2} fill={color}>
            <title>{`${xLabel}: ${p[0].toFixed(3)}, ${yLabel}: ${p[1].toFixed(3)}`}</title>
          </circle>
        ))}
        <text x="240" y="257" textAnchor="middle">
          {xLabel}
        </text>
        <text transform="translate(12 130) rotate(-90)" textAnchor="middle">
          {yLabel}
        </text>
      </svg>
    </figure>
  );
}
export function Confusion({ values }: { values: number[][] }) {
  return (
    <div className="confusion" aria-label="Confusion matrix">
      <p className="muted">Rows: actual · columns: predicted</p>
      <div className="matrix">
        <span></span>
        <small>Legitimate</small>
        <small>Phishing</small>
        <small>Legitimate</small>
        <div className="correct">
          {values[0][0].toLocaleString()}
          <small>True negatives</small>
        </div>
        <div>
          {values[0][1].toLocaleString()}
          <small>False positives</small>
        </div>
        <small>Phishing</small>
        <div>
          {values[1][0].toLocaleString()}
          <small>False negatives</small>
        </div>
        <div className="correct">
          {values[1][1].toLocaleString()}
          <small>True positives</small>
        </div>
      </div>
    </div>
  );
}
