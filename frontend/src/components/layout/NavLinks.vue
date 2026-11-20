<script setup lang="ts">
import { storeToRefs } from "pinia";
import AppIcon from "@/components/ui/AppIcon.vue";
import { NAV_ITEMS, type NavItem } from "@/constants/navigation";
import { useDashboardStore } from "@/stores/dashboard";

/**
 * Navigation list shared by the desktop sidebar (vertical) and the mobile bar (horizontal).
 * The sun indicator bar always exists and only scales in/out → switching pages eases instead of blinking.
 */
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
            'relative flex items-center gap-3 whitespace-nowrap rounded-lg font-medium transition-colors duration-base',
            orientation === 'vertical'
              ? [
                  'px-3 py-2.5 text-base text-side-fg hover:bg-white/5 hover:text-white',
                  'before:absolute before:inset-y-2 before:left-0 before:w-1 before:scale-y-0 before:rounded-full before:bg-sun before:transition-transform before:duration-base',
                ]
              : 'px-3 py-2 text-sm text-muted hover:bg-mist hover:text-fg',
          ]"
          :active-class="orientation === 'vertical' ? '!bg-sun/15 !text-sun font-semibold before:!scale-y-100' : '!bg-fg !text-bg font-semibold'"
        >
          <AppIcon :name="item.icon" :size="orientation === 'vertical' ? 20 : 18" />
          <span class="flex-1">{{ item.label }}</span>
          <Transition name="fade">
            <span
              v-if="badge(item)"
              :class="[
                'min-w-[1.5rem] rounded-full px-1.5 text-center text-caption font-bold leading-6',
                item.badge === 'pendingActions'
                  ? 'bg-sun text-sun-on'
                  : orientation === 'vertical' ? 'bg-white/10 text-white' : 'bg-mist text-mist-fg',
              ]"
            >{{ badge(item) }}</span>
          </Transition>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
