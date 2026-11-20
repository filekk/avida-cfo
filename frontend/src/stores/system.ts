import { defineStore } from "pinia";
import { ref } from "vue";
import { getConfig, getLlmHealth } from "@/api";
import type { AppConfig, LlmHealth } from "@/types/api";

/** Backend/runtime info: model name, demo date, "AI online" indicator. */
export const useSystemStore = defineStore("system", () => {
  const config = ref<AppConfig | null>(null);
  const llm = ref<LlmHealth | null>(null);
  const llmChecking = ref(false);

  async function loadConfig() {
    try {
      config.value = await getConfig();
    } catch {
      config.value = null;
    }
  }

  async function checkLlm() {
    llmChecking.value = true;
    try {
      llm.value = await getLlmHealth();
    } catch {
      llm.value = { ok: false, reason: "Backend unreachable" };
    } finally {
      llmChecking.value = false;
    }
  }

  return { config, llm, llmChecking, loadConfig, checkLlm };
});
