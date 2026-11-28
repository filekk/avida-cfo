#!/usr/bin/env bash
# Collects everything needed to choose the model and serving setup.
# Usage (after `oc login`): bash deploy/check-cluster.sh > cluster-info.txt
# No `-e`: the script reports what it can see and carries on. `pipefail` makes the `|| echo …` fallbacks fire
# when `oc` fails in front of `head` / `awk` (otherwise the last command's exit 0 hides the failure).
set -uo pipefail

section() { printf '\n===== %s =====\n' "$1"; }

oc whoami >/dev/null 2>&1 || { echo "Not logged in – run 'oc login' first." >&2; exit 1; }

section "WHO / CLUSTER"
oc whoami; oc whoami --show-server; oc version 2>/dev/null | tail -2

section "NODES (CPU / RAM / GPU allocatable)"
oc get nodes -o custom-columns='NAME:.metadata.name,CPU:.status.allocatable.cpu,MEM:.status.allocatable.memory,GPU:.status.allocatable.nvidia\.com/gpu'

section "GPU MODEL / VRAM (labels from NVIDIA GPU Feature Discovery)"
oc get nodes -L nvidia.com/gpu.product -L nvidia.com/gpu.memory -L nvidia.com/gpu.count -L nvidia.com/mig.strategy

section "GPU / AI OPERATORS"
oc get csv -A --no-headers 2>/dev/null | awk '{print $2, $NF}' | sort -u | grep -Ei 'gpu|nfd|rhods|opendatahub|serverless|servicemesh|authorino|devspaces|kueue|llm' || echo "none matched"

section "NVIDIA DRIVER PODS"
oc get pods -n nvidia-gpu-operator --no-headers 2>/dev/null | head -20 || echo "namespace nvidia-gpu-operator not found"

section "OPENSHIFT AI COMPONENTS (DataScienceCluster)"
if oc get datasciencecluster -o name 2>/dev/null | grep -q .; then
  oc get datasciencecluster -o yaml | grep -B1 managementState | grep -v '^--' || echo "no component states found"
else
  echo "no DataScienceCluster visible (permissions?)"
fi

section "SERVING RUNTIME TEMPLATES (look for vLLM)"
oc get templates -n redhat-ods-applications --no-headers 2>/dev/null | awk '{print $1}' | grep -i -E 'vllm|runtime' || echo "not visible"

section "HARDWARE PROFILES / ACCELERATOR PROFILES"
oc get hardwareprofiles -A 2>/dev/null || true
oc get acceleratorprofiles -A 2>/dev/null || true

section "STORAGE CLASSES"
oc get sc

section "EXISTING INFERENCE SERVICES"
oc get inferenceservice -A 2>/dev/null || echo "none / CRD missing"
