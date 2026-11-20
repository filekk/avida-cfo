# Deploying Avida CFO on Red Hat OpenShift AI

Two projects (namespaces):

| Namespace | What runs there |
|---|---|
| `avida-models` | vLLM InferenceService with the open-weights model (RHOAI Data Science Project) |
| `avida-cfo` | the app (FastAPI + Vue in one container) |

## 1. Model on vLLM (hard criterion + bonus)

Our cluster: 1 node, 32 CPU, ~121 GB RAM, **1x NVIDIA L4 (24 GB)**. Check yours with `bash deploy/check-cluster.sh`.

We serve **Granite 3.3 8B Instruct** (bf16, fits the L4) from the Red Hat modelcar catalog with the
RHOAI vLLM runtime (`registry.redhat.io/rhaiis/vllm-cuda-rhel9`):

```bash
oc apply -f deploy/model/granite-8b.yaml          # Namespace + ServingRuntime + InferenceService
oc -n avida-models get isvc granite-8b -w         # first start: ~15 min (16 GB image pull)
```

- Endpoint (cluster-internal, no auth): `http://granite-8b-predictor.avida-models.svc.cluster.local:8080/v1`, model name `granite-8b`.
- Only one GPU: any other model holding it must be stopped first
  (`oc annotate isvc <name> -n <ns> serving.kserve.io/stop=true --overwrite`; `=false` starts it again).
  We stopped the sample `llama-32-3b-instruct` in `my-first-model`.
- Shows up in the OpenShift AI dashboard under *Data Science Projects → avida-models → Models*.
- Other modelcars: `quay.io/redhat-ai-services/modelcar-catalog:<tag>` (e.g. `qwen3-8b`, `granite-4.0-h-tiny`).

Test from inside the cluster (the app pod has Python):
```bash
oc -n avida-cfo exec deploy/avida-cfo -- python -c "import urllib.request as u;print(u.urlopen('http://granite-8b-predictor.avida-models.svc.cluster.local:8080/v1/models').read().decode())"
```

## 2. App

```bash
oc login --token=... --server=...
oc new-project avida-cfo

# Builds the root Dockerfile inside OpenShift (frontend + backend in one image)
oc new-app https://github.com/<org>/avida-cfo.git --name=avida-cfo --strategy=docker
oc logs -f bc/avida-cfo

# Configuration (edit LLM_BASE_URL / LLM_MODEL first)
oc apply -f deploy/configmap.yaml
oc set env deploy/avida-cfo --from=configmap/avida-cfo-config

# HTTPS route with a longer timeout for the SSE agent trace
oc create route edge avida-cfo --service=avida-cfo --port=8080
oc annotate route avida-cfo haproxy.router.openshift.io/timeout=180s
oc get route avida-cfo -o jsonpath='{.spec.host}'
```

Private repo? Add a source secret:
`oc create secret generic gh --from-literal=username=<user> --from-literal=password=<PAT> --type=kubernetes.io/basic-auth`
and `oc new-app ... --source-secret=gh`.

Rebuild after a push: `oc start-build avida-cfo --follow`.

## 3. Verify

```bash
HOST=$(oc get route avida-cfo -o jsonpath='{.spec.host}')
curl -s https://$HOST/api/health
curl -s https://$HOST/api/llm/health     # must list the model -> "ok": true
curl -N https://$HOST/api/sync           # streams the agent trace
```

If `/api/llm/health` is not ok, the app still works on cached answers (`DEMO_FALLBACK=true`) and the
UI marks them "(cached answer)". For judging, make sure it is **ok** – the model must really be used.

## 4. Jupyter workbench (bonus)

*Data Science Projects* → `avida-models` → **Create workbench** (Standard Data Science image, small size, no GPU)
→ clone the repo → run `notebooks/contract_extraction.ipynb`.

## 5. Dev Spaces (bonus)

Install the **Red Hat OpenShift Dev Spaces** operator (OperatorHub) → create a `CheCluster` with defaults →
open the Dev Spaces dashboard → *Create Workspace* from the repo URL (uses `.devfile.yaml`).
For the OSS-assistant bonus, install the *Continue* extension and point it at the same vLLM endpoint
(OpenAI-compatible provider, `apiBase` = `LLM_BASE_URL`).

Resource tip: single node with 32 CPU / 128 GB. Model + app + workbench + Dev Spaces fit; don't enable
llm-d, MaaS and guardrails on top.
