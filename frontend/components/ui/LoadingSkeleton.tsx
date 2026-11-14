interface LoadingSkeletonProps {
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({
  rows = 3,
  className = "h-28",
}: LoadingSkeletonProps) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className={`animate-pulse rounded-card bg-slate-200/70 ${className}`}
        />
      ))}
    </div>
  );
}
