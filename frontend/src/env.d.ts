/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional absolute API origin; empty = same-origin /api. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
