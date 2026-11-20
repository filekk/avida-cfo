import type { AppConfig, AuditEntry, LlmHealth, PolicyRule } from "@/types/api";
import { http } from "./http";

/** GET /api/health → {"status":"ok"} */
export const getHealth = () => http.get<{ status: string }>("/health");

/** GET /api/llm/health – drives the small "AI online" indicator. */
export const getLlmHealth = () => http.get<LlmHealth>("/llm/health");

/** GET /api/config – model name, forecast days, demo "today". */
export const getConfig = () => http.get<AppConfig>("/config");

/** GET /api/policy – the autonomy matrix ("who may do what"). */
export const getPolicy = () => http.get<PolicyRule[]>("/policy");

/** GET /api/audit – what happened, in order. */
export const getAudit = () => http.get<AuditEntry[]>("/audit");
