import type { Dashboard } from "@/types/api";
import { http } from "./http";

/** GET /api/dashboard – start screen (forecast; findings/actions after a sync). */
export const getDashboard = (signal?: AbortSignal) => http.get<Dashboard>("/dashboard", signal);

/** POST /api/reset – clears findings/actions, returns the start dashboard. Use before every demo run. */
export const resetDemo = () => http.post<Dashboard>("/reset");
