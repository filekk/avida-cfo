import { onMounted, ref, shallowRef, type Ref } from "vue";
import { errorMessage } from "@/api";

/**
 * Loads view-local data (things that don't belong in a global store, e.g. /api/policy, /api/audit).
 *   const { data, loading, error, reload } = useAsyncData(getPolicy);
 * Only the newest reload writes: a slow, older answer (e.g. the list from before a delete) never overwrites it.
 */
export function useAsyncData<T>(fetcher: () => Promise<T>, { immediate = true } = {}) {
  const data = shallowRef<T | null>(null) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<string | null>(null);
  let run = 0;

  async function reload() {
    const mine = ++run;
    loading.value = true;
    error.value = null;
    try {
      const value = await fetcher();
      if (mine === run) data.value = value;
    } catch (e) {
      if (mine === run) error.value = errorMessage(e);
    } finally {
      if (mine === run) loading.value = false;
    }
  }

  /** Set the data directly (e.g. from a mutation's response) – also outdates any reload still in flight. */
  function set(value: T) {
    run++;
    loading.value = false;
    data.value = value;
  }

  if (immediate) onMounted(reload);
  return { data, loading, error, reload, set };
}
