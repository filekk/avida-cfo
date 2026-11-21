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
# IMPORTANT: without an explicit ref, the GitHub webhook only reacts to pushes to "master"
# and silently ignores "main" (HTTP 200, but no build).
oc patch bc avida-cfo --type=merge -p '{"spec":{"source":{"git":{"ref":"main"}}}}'
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

The notebook is the **evaluation harness of the production extractor**: it imports `backend/app/extraction.py`
(the code behind `POST /api/contracts/upload`), runs it on the vLLM model and benchmarks it against the
hand-labelled `contracts_index.json` (results in `notebooks/benchmark_results.json`). The last cell can upload a
contract to the running app through the internal service (`http://avida-cfo.avida-cfo.svc.cluster.local:8080`).
Change the prompt/schema in the backend → re-run the notebook → see whether accuracy went up or down.

## 5. Dev Spaces (bonus)

Install the **Red Hat OpenShift Dev Spaces** operator (OperatorHub) → create a `CheCluster` with defaults →
open the Dev Spaces dashboard → *Create Workspace* from the repo URL (uses `.devfile.yaml`).
For the OSS-assistant bonus, install the *Continue* extension and point it at the same vLLM endpoint
(OpenAI-compatible provider, `apiBase` = `LLM_BASE_URL`).

Resource tip: single node with 32 CPU / 128 GB. Model + app + workbench + Dev Spaces fit; don't enable
llm-d, MaaS and guardrails on top.

## 6. MLflow: tracing and evaluating the agents (bonus)

**Server** (namespace `avida-cfo`, next to the app):
```bash
oc apply -n avida-cfo -f deploy/mlflow.yaml        # PVC + Deployment + Service + Route
oc rollout status -n avida-cfo deploy/mlflow
oc get route -n avida-cfo mlflow -o jsonpath='{.spec.host}'   # MLflow UI
```

**Tracing** (`backend/app/tracing.py`): every inbox check becomes one MLflow trace
`sync_inbox → analyst.read_email / legal.check / negotiation · <party> → negotiator.draft / legal.review_draft → llm.json|llm.text`
with prompts, answers, token usage, latency and `avida.source` = `llm` / `fallback` / `rules` on every agent span.
"Ask your CFO" (`ask_cfo`) and contract uploads (`contract_upload`) are traced too.
It is switched on by `MLFLOW_TRACKING_URI` (see `deploy/configmap.yaml`) and is strictly optional:
not set, package missing or server down → no-op, the app behaves exactly as before.
Check: `curl -s https://$HOST/api/tracing/health`.

**Evaluation** (`backend/eval/evaluate_agents.py`): `mlflow.genai.evaluate` runs the real agent chain on the
hand-labelled demo inbox and scores every agent (category, party, figures, verdict, clause, draft rules,
legal approval, share of steps answered by the model). Results: MLflow UI → experiment `avida-cfo-agent-eval`.
```bash
oc port-forward -n avida-cfo svc/mlflow 5000:5000 &
oc port-forward -n avida-models svc/granite-8b-predictor 8000:8080 &
cd backend && pip install -r eval/requirements.txt
MLFLOW_TRACKING_URI=http://localhost:5000 LLM_BASE_URL=http://localhost:8000/v1 python eval/evaluate_agents.py
```
