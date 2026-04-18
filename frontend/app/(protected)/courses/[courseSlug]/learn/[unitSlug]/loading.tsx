export default function LearningUnitLoading() {
  return (
    <div className="flex h-[calc(100vh-4.5rem)] items-center justify-center -mx-4 -mt-4 md:-mx-6 md:-mt-6">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Loading learning unit...
        </p>
      </div>
    </div>
  );
}
