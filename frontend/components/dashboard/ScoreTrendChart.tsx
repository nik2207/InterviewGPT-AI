import type { ScoreTrendPoint } from "@/lib/api/dashboard";

interface ScoreTrendChartProps {
  points: ScoreTrendPoint[];
}

export function ScoreTrendChart({ points }: ScoreTrendChartProps) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-app-muted">
        Complete more interviews to see score trends.
      </p>
    );
  }

  const max = 100;
  return (
    <div
      className="flex h-40 items-end gap-2"
      role="img"
      aria-label="Interview scores over recent sessions"
    >
      {points.map((point) => {
        const height = Math.max(8, Math.round((point.score / max) * 100));
        return (
          <div key={`${point.label}-${point.score}`} className="flex flex-1 flex-col items-center gap-2">
            <div
              className="w-full max-w-[2.5rem] rounded-t-md bg-gradient-to-t from-app-primary to-indigo-400"
              style={{ height: `${height}%` }}
              title={`${point.label}: ${point.score}/100`}
            />
            <span className="text-[10px] text-app-muted">{point.label}</span>
          </div>
        );
      })}
    </div>
  );
}
