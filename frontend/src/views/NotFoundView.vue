<script setup lang="ts">
import BaseButton from "@/components/ui/BaseButton.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import { t } from "@/i18n";
</script>

<template>
  <EmptyState icon="alert" :title="t('This page doesn\'t exist')" :description="t('The link may be outdated.')">
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowLeft">{{ t("Back to overview") }}</BaseButton>
  </EmptyState>
</template>
