export function StatusBadge({ value }: { value: string | null | undefined }) {
  const normalized = (value ?? "unknown").toLowerCase();
  return <span className={`badge ${normalized}`}>{normalized.replace("_", " ")}</span>;
}
