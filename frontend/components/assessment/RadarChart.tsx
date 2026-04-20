// components/assessment/RadarChart.tsx
// Pure SVG radar / spider chart — zero external dependencies.
// Renders a polygon for topic mastery scores on a multi-axis grid.

interface RadarDataPoint {
  label: string;
  value: number;      // 0 – 100  (score_percent)
  level: string;      // mastery level label shown in tooltip
}

interface Props {
  data: RadarDataPoint[];
  size?: number;      // outer SVG size (square); defaults to 320
}

// ---------------------------------------------------------------------------
// Maths helpers
// ---------------------------------------------------------------------------

/** Convert polar (degrees from top, radius) to Cartesian SVG coords. */
function polar(deg: number, r: number, cx: number, cy: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Build an SVG polygon points string from an array of {x,y}. */
function toPoints(pts: { x: number; y: number }[]) {
  return pts.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
}

import { SKILL_COLORS, BRAND_PRIMARY } from "@/lib/ui/skillColors";

const GRID_LEVELS = [20, 40, 60, 80, 100] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RadarChart({ data, size = 320 }: Props) {
  if (data.length === 0) return null;

  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.34;        // radius of the outermost grid ring
  const labelR = maxR + size * 0.14; // radius for axis labels

  const N = data.length;
  const angleStep = 360 / N;

  // ── Grid polygons ──────────────────────────────────────────────────────────
  const gridPolygons = GRID_LEVELS.map((pct) => {
    const pts = Array.from({ length: N }, (_, i) =>
      polar(angleStep * i, (pct / 100) * maxR, cx, cy)
    );
    return { pct, pts };
  });

  // ── Axis lines ─────────────────────────────────────────────────────────────
  const axes = Array.from({ length: N }, (_, i) => ({
    end: polar(angleStep * i, maxR, cx, cy),
  }));

  // ── Data polygon ───────────────────────────────────────────────────────────
  const dataPoints = data.map((d, i) =>
    polar(angleStep * i, (Math.min(d.value, 100) / 100) * maxR, cx, cy)
  );

  // ── Labels ─────────────────────────────────────────────────────────────────
  const labels = data.map((d, i) => {
    const angle = angleStep * i;
    const pos = polar(angle, labelR, cx, cy);
    // Anchor: left-align for right-side labels, right-align for left-side
    const anchor: "middle" | "start" | "end" =
      Math.abs(pos.x - cx) < 4 ? "middle" : pos.x > cx ? "start" : "end";
    return { ...d, ...pos, anchor, angle };
  });

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      style={{ maxWidth: size }}
      aria-label="Mastery radar chart"
      role="img"
    >
      {/* ── Grid rings ── */}
      {gridPolygons.map(({ pct, pts }) => (
        <polygon
          key={pct}
          points={toPoints(pts)}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.12}
          strokeWidth={1}
          className="text-slate-600 dark:text-slate-400"
        />
      ))}

      {/* ── Grid ring labels (20 / 40 / …) ── */}
      {gridPolygons.map(({ pct, pts }) => (
        <text
          key={`label-${pct}`}
          x={(pts[0].x + cx) / 2}
          y={(pts[0].y + cy) / 2}
          textAnchor="middle"
          fontSize={size * 0.034}
          fill="currentColor"
          fillOpacity={0.35}
          className="text-slate-500"
        >
          {pct}
        </text>
      ))}

      {/* ── Axis lines ── */}
      {axes.map((ax, i) => (
        <line
          key={i}
          x1={cx}
          y1={cy}
          x2={ax.end.x}
          y2={ax.end.y}
          stroke="currentColor"
          strokeOpacity={0.15}
          strokeWidth={1}
          className="text-slate-500"
        />
      ))}

      {/* ── Data polygon fill ── */}
      <polygon
        points={toPoints(dataPoints)}
        fill={BRAND_PRIMARY}
        fillOpacity={0.18}
        stroke={BRAND_PRIMARY}
        strokeWidth={2}
        strokeLinejoin="round"
      />

      {/* ── Data point dots ── */}
      {dataPoints.map((pt, i) => {
        const color = SKILL_COLORS[data[i].level] ?? BRAND_PRIMARY;
        return (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r={size * 0.022}
            fill={color}
            stroke="white"
            strokeWidth={1.5}
          />
        );
      })}

      {/* ── Axis labels ── */}
      {labels.map((lb, i) => (
        <g key={i}>
          <text
            x={lb.x}
            y={lb.y - size * 0.012}
            textAnchor={lb.anchor}
            fontSize={size * 0.042}
            fontWeight="600"
            fill="currentColor"
            fillOpacity={0.85}
            className="text-slate-700 dark:text-slate-200"
          >
            {lb.label.length > 14 ? lb.label.slice(0, 13) + "…" : lb.label}
          </text>
          <text
            x={lb.x}
            y={lb.y + size * 0.046}
            textAnchor={lb.anchor}
            fontSize={size * 0.036}
            fill={SKILL_COLORS[lb.level] ?? BRAND_PRIMARY}
            fontWeight="700"
          >
            {lb.value.toFixed(0)}%
          </text>
        </g>
      ))}

      {/* ── Center dot ── */}
      <circle cx={cx} cy={cy} r={3} fill={BRAND_PRIMARY} fillOpacity={0.5} />
    </svg>
  );
}
