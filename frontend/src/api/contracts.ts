import type { ContractSummary, UploadResult } from "@/types/api";
import { apiUrl, http } from "./http";

/**
 * The Legal Agent's knowledge base. See docs/API.md → "Contracts: upload → live extraction → Legal Agent".
 * Uploads are kept in memory: POST /api/reset removes them. The next /api/sync uses an uploaded contract.
 */

/** File-picker filter: the same types as `FILE_TYPES` (components/contracts/files.ts) and the backend accept. */
export const CONTRACT_ACCEPT = ".pdf,.md,.txt";

/** GET /api/contracts – uploads first, then the notebook-prepared index. */
export const getContracts = (signal?: AbortSignal) => http.get<ContractSummary[]>("/contracts", signal);

/**
 * POST /api/contracts/upload (multipart `file`) – the model reads the contract, 10–20 s → show a progress state.
 * Unreadable file / scanned PDF / model down with an unknown contract → ApiError 422 with a readable `message`.
 * Uploading the same party again replaces the earlier upload (same id).
 */
export const uploadContract = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return http.post<UploadResult>("/contracts/upload", form);
};

/** DELETE /api/contracts/{id} – only uploaded contracts (U-001…); index contracts → 404. Returns the new list. */
export const deleteContract = (id: string) => http.del<ContractSummary[]>(`/contracts/${encodeURIComponent(id)}`);

/**
 * GET /api/contracts/{id}/file – the original file: `inline` opens it in the browser (preview),
 * `download` saves it. Plain URLs for <a href>, so the browser does the work (no fetch, no blob).
 */
export const contractFileUrl = (id: string, download = false) =>
  apiUrl(`/contracts/${encodeURIComponent(id)}/file${download ? "?download=true" : ""}`);
