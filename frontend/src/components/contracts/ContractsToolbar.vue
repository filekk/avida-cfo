<script setup lang="ts">
import { useId } from "vue";
import AppIcon from "@/components/ui/AppIcon.vue";
import { t } from "@/i18n";
import { DATE_OPTIONS, SIZE_OPTIONS, isFiltered, typeMeta, type FileFilters } from "./files";

/**
 * Toolbar above the contracts table: search by name (live) · type chips · added when · size.
 * Plain native controls (big, readable, keyboard and screen-reader friendly), one line on wide screens,
 * wraps cleanly on narrow ones (search gets its own line on phones).
 * `types` = the file types to offer as chips (the ones in the list + what can be uploaded).
 */
const filters = defineModel<FileFilters>({ required: true });
defineProps<{ types: string[]; shown: number; total: number }>();
const emit = defineEmits<{ clear: [] }>();

const uid = useId();
const set = <K extends keyof FileFilters>(k: K, v: FileFilters[K]) => (filters.value = { ...filters.value, [k]: v });

const SELECT =
  "min-h-11 rounded-lg border border-line bg-surface pl-3 pr-8 text-sm font-medium text-fg transition-colors duration-fast hover:border-fg/40 focus:border-fg/40";
</script>

<template>
  <div class="grid gap-3" role="search" :aria-label="t('Find a contract')">
    <div class="flex flex-wrap items-center gap-2">
      <!-- live search -->
      <label :for="`q-${uid}`" class="sr-only">{{ t("Search by name") }}</label>
      <span class="relative w-full min-w-0 sm:w-auto sm:flex-1 lg:max-w-sm">
        <AppIcon name="search" :size="18" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          :id="`q-${uid}`"
          :value="filters.q"
          type="search"
          autocomplete="off"
          :placeholder="t('Search by name or company')"
          class="min-h-11 w-full rounded-lg border border-line bg-input pl-10 pr-3 text-fg placeholder:text-muted focus:border-fg/40"
          @input="set('q', ($event.target as HTMLInputElement).value)"
        />
      </span>

      <!-- added when -->
      <label :for="`date-${uid}`" class="sr-only">{{ t("Added") }}</label>
      <select :id="`date-${uid}`" :class="SELECT" :value="filters.date" @change="set('date', ($event.target as HTMLSelectElement).value as FileFilters['date'])">
        <option v-for="o in DATE_OPTIONS" :key="o.value" :value="o.value">{{ t(o.label) }}</option>
      </select>

      <!-- size -->
      <label :for="`size-${uid}`" class="sr-only">{{ t("File size") }}</label>
      <select :id="`size-${uid}`" :class="SELECT" :value="filters.size" @change="set('size', ($event.target as HTMLSelectElement).value as FileFilters['size'])">
        <option v-for="o in SIZE_OPTIONS" :key="o.value" :value="o.value">{{ t(o.label) }}</option>
      </select>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <!-- type chips -->
      <div class="flex flex-wrap items-center gap-2" role="group" :aria-label="t('File type')">
        <button
          v-for="ty in ['all', ...types]"
          :key="ty"
          type="button"
          :aria-pressed="filters.type === ty"
          :class="[
            'flex min-h-10 items-center gap-1.5 rounded-lg border px-3 text-sm font-semibold transition-colors duration-fast',
            filters.type === ty ? 'border-fg bg-fg text-bg' : 'border-line bg-surface text-fg hover:border-fg/40 hover:bg-input/60',
          ]"
          @click="set('type', ty)"
        >
          <AppIcon v-if="ty !== 'all'" :name="typeMeta(ty).icon" :size="16" />
          {{ ty === "all" ? t("All") : typeMeta(ty).label }}
        </button>
      </div>

      <p class="flex items-center gap-3 text-label text-muted" aria-live="polite">
        <span>{{ t("{shown} of {total} files", { shown, total }) }}</span>
        <button
          v-if="isFiltered(filters)"
          type="button"
          class="flex min-h-10 items-center gap-1 rounded-lg px-2 font-semibold text-gold underline-offset-4 hover:underline"
          @click="emit('clear')"
        >
          <AppIcon name="x" :size="16" />{{ t("Clear filters") }}
        </button>
      </p>
    </div>
  </div>
</template>
