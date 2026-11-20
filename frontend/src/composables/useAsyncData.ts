import { onMounted, ref, shallowRef, type Ref } from "vue";
import { ApiError } from "@/api";

/**
 * Loads view-local data (things that don't belong in a global store, e.g. /api/policy, /api/audit).
 *   const { data, loading, error, reload } = useAsyncData(getPolicy);
 */
export function useAsyncData<T>(fetcher: () => Promise<T>, { immediate = true } = {}) {
  const data = shallowRef<T | null>(null) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function reload() {
    loading.value = true;
    error.value = null;
    try {
      data.value = await fetcher();
    } catch (e) {
      error.value = e instanceof ApiError || e instanceof Error ? e.message : "Something went wrong.";
    } finally {
      loading.value = false;
    }
  }

  if (immediate) onMounted(reload);
  return { data, loading, error, reload };
}
