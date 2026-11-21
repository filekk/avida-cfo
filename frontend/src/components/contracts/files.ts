import type { IconName } from "@/components/ui/icons";
import { t } from "@/i18n";
import type { ContractSummary } from "@/types/api";

/**
 * Contracts page as a small file explorer: filters, sorting and file checks. Pure functions, no API calls.
 * Labels stay English here and are translated where they are rendered (never call t() at module level),
 * except `validateFile`, which is called on user action and returns a ready message.
 */

// --- file types ------------------------------------------------------------------------------------
/** What the backend accepts (POST /api/contracts/upload). Word / Excel are not readable by the Legal Agent. */
export const FILE_TYPES = ["pdf", "md", "txt"] as const;

export const TYPE_META: Record<string, { label: string; icon: IconName; name: string }> = {
  pdf: { label: "PDF", icon: "document", name: "PDF document" },
  md: { label: "MD", icon: "fileCode", name: "Markdown text" },
  txt: { label: "TXT", icon: "fileType", name: "Plain text" },
};
export const typeMeta = (type: string) =>
  TYPE_META[type] ?? { label: type.toUpperCase() || "?", icon: "document" as IconName, name: "File" };

/** Size limit of the upload (5 MB, same as the backend). */
export const MAX_BYTES = 5 * 1024 * 1024;

/** Check type and size before sending, so the owner gets an instant, plain message instead of a 422 later. */
export function validateFile(f: File): string | null {
  const dot = f.name.lastIndexOf(".");
  const ext = dot > 0 ? f.name.slice(dot + 1).toLowerCase() : ""; // a file called "pdf" has no type
  if (!(FILE_TYPES as readonly string[]).includes(ext)) return t("Please choose a PDF or a text file (.txt, .md).");
  if (f.size > MAX_BYTES) return t("This file is larger than 5 MB. Please choose a smaller one.");
  return null;
}

// --- filters -------------------------------------------------------------------------------------
export type DateFilter = "any" | "today" | "7d" | "30d";
export type SizeFilter = "any" | "small" | "medium" | "large";
export interface FileFilters {
  q: string;
  type: "all" | string;
  date: DateFilter;
  size: SizeFilter;
}
export const NO_FILTERS: FileFilters = { q: "", type: "all", date: "any", size: "any" };
export const isFiltered = (f: FileFilters) => f.q.trim() !== "" || f.type !== "all" || f.date !== "any" || f.size !== "any";

export const DATE_OPTIONS: { value: DateFilter; label: string }[] = [
  { value: "any", label: "Any time" },
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];
export const SIZE_OPTIONS: { value: SizeFilter; label: string }[] = [
  { value: "any", label: "Any size" },
  { value: "small", label: "Small (under 1 MB)" },
  { value: "medium", label: "Medium (1–5 MB)" },
  { value: "large", label: "Large (over 5 MB)" },
];

const MB = 1024 * 1024;
const DAY = 86_400_000;

function matchesDate(c: ContractSummary, f: DateFilter, now: number): boolean {
  if (f === "any") return true;
  if (!c.uploaded_at) return false; // prepared by Avida, no upload date
  const at = new Date(c.uploaded_at).getTime();
  if (f === "today") return new Date(at).toDateString() === new Date(now).toDateString();
  return now - at <= (f === "7d" ? 7 : 30) * DAY;
}
function matchesSize(c: ContractSummary, f: SizeFilter): boolean {
  if (f === "any") return true;
  const b = c.size_bytes ?? 0;
  return f === "small" ? b < MB : f === "medium" ? b >= MB && b <= 5 * MB : b > 5 * MB;
}

/** Name search: title, file name and the other party ("cloudhost" finds the CloudHost contract). */
export function applyFilters(list: ContractSummary[], f: FileFilters, now = Date.now()): ContractSummary[] {
  const q = f.q.trim().toLowerCase();
  return list.filter(
    (c) =>
      (!q || [c.title, c.file_name, c.party].some((s) => s?.toLowerCase().includes(q))) &&
      (f.type === "all" || c.file_type === f.type) &&
      matchesDate(c, f.date, now) &&
      matchesSize(c, f.size),
  );
}

// --- sorting -------------------------------------------------------------------------------------
export type SortKey = "name" | "type" | "date" | "size";
export interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}
/** Default: newest first (uploads on top, the prepared contracts below). */
export const DEFAULT_SORT: SortState = { key: "date", dir: "desc" };

const value = (c: ContractSummary, k: SortKey): string | number | null => {
  switch (k) {
    case "name":
      return c.title.toLowerCase();
    case "type":
      return c.file_type;
    case "date":
      return c.uploaded_at ? new Date(c.uploaded_at).getTime() : null;
    case "size":
      return c.size_bytes;
  }
};

/** Empty values (no upload date, unknown size) always go last, whatever the direction. */
export function applySort(list: ContractSummary[], s: SortState): ContractSummary[] {
  const sign = s.dir === "asc" ? 1 : -1;
  return [...list].sort((a, b) => {
    const x = value(a, s.key);
    const y = value(b, s.key);
    if (x === null && y === null) return a.title.localeCompare(b.title);
    if (x === null) return 1;
    if (y === null) return -1;
    if (x === y) return a.title.localeCompare(b.title);
    return (x < y ? -1 : 1) * sign;
  });
}
/** Click on a header: same column → flip; new column → names / types A→Z, dates / sizes biggest first. */
export const nextSort = (s: SortState, key: SortKey): SortState =>
  s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" || key === "type" ? "asc" : "desc" };
