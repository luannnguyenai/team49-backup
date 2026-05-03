export function formatDurationFromHours(hours: number | null | undefined): string | null {
  if (hours == null || !Number.isFinite(hours) || hours <= 0) return null;

  const totalSeconds = Math.max(1, Math.round(hours * 60 * 60));
  const hourCount = Math.floor(totalSeconds / 3600);
  const minuteCount = Math.floor((totalSeconds % 3600) / 60);
  const secondCount = totalSeconds % 60;
  const parts: string[] = [];

  if (hourCount > 0) parts.push(`${hourCount} hr`);
  if (minuteCount > 0) parts.push(`${minuteCount} min`);
  if (secondCount > 0 && hourCount === 0) parts.push(`${secondCount} sec`);

  return parts.length > 0 ? parts.join(" ") : "1 sec";
}
