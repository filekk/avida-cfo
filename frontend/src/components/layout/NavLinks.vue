<script setup lang="ts">
import { storeToRefs } from "pinia";
import AppIcon from "@/components/ui/AppIcon.vue";
import { NAV_ITEMS, type NavItem } from "@/constants/navigation";
import { useDashboardStore } from "@/stores/dashboard";

/** Navigation list shared by the desktop sidebar (vertical) and the mobile bar (horizontal). */
withDefaults(defineProps<{ orientation?: "vertical" | "horizontal" }>(), { orientation: "vertical" });

const { pendingActions, findings } = storeToRefs(useDashboardStore());
const badge = (item: NavItem) =>
  item.badge === "pendingActions" ? pendingActions.value.length : item.badge === "findings" ? findings.value.length : 0;
</script>

<template>
  <nav :aria-label="'Main'">
    <ul :class="orientation === 'vertical' ? 'grid gap-1' : 'flex gap-1 overflow-x-auto'">
      <li v-for="item in NAV_ITEMS" :key="item.to">
        <RouterLink
          :to="{ name: item.to }"
          :class="[
            'relative flex items-center gap-3 whitespace-nowrap rounded-lg font-medium transition-colors',
            orientation === 'vertical'
              ? 'px-3 py-2.5 text-[0.9rem] text-side-fg hover:bg-white/5 hover:text-white'
              : 'px-2.5 py-2 text-[0.88rem] text-muted hover:bg-mist hover:text-fg',
          ]"
          :active-class="
            orientation === 'vertical'
              ? '!bg-sun/15 !text-sun font-semibold before:absolute before:inset-y-2 before:left-0 before:w-1 before:rounded-full before:bg-sun'
              : '!bg-fg !text-bg font-semibold'
          "
        >
          <AppIcon :name="item.icon" :size="18" />
          <span class="flex-1">{{ item.label }}</span>
          <span
            v-if="badge(item)"
            :class="[
              'min-w-[1.25rem] rounded-full px-1.5 text-center text-[0.7rem] font-bold leading-5',
              item.badge === 'pendingActions'
                ? 'bg-sun text-sun-on'
                : orientation === 'vertical' ? 'bg-white/10' : 'bg-mist text-mist-fg',
            ]"
          >{{ badge(item) }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
