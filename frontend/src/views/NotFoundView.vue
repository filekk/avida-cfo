<script setup lang="ts">
import BaseButton from "@/components/ui/BaseButton.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
</script>

<template>
  <EmptyState icon="alert" title="This page doesn't exist" description="The link may be outdated.">
    <BaseButton :to="{ name: 'dashboard' }" icon="arrowLeft">Back to overview</BaseButton>
  </EmptyState>
</template>
