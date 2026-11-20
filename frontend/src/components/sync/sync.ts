import { t } from "@/i18n";

/** The inbox check as the owner sees it. */
export type SyncState = "idle" | "running" | "done" | "error";

/**
 * Error messages created by the front-end itself are translated; messages sent by the backend are shown as sent
 * (they are not in the dictionary – translating them would only pollute the missing-strings list).
 */
const OWN_ERRORS = new Set([
  "Connection to the assistant was lost.",
  "Something went wrong.",
  "Cannot reach the server. Check your connection.",
]);
export const errorText = (msg: string | null | undefined) => (msg ? (OWN_ERRORS.has(msg) ? t(msg) : msg) : "");
