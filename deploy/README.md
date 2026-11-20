# Deploying Avida CFO on Red Hat OpenShift AI

Two projects (namespaces):

| Namespace | What runs there |
|---|---|
| `avida-models` | vLLM InferenceService with the open-weights model (RHOAI Data Science Project) |
| `avida-cfo` | the app (FastAPI + Vue in one container) |

## 1. Model on vLLM (hard criterion + bonus)

In the **OpenShift AI dashboard**:

1. *Data Science Projects* → **Create project** `avida-models`.
2. Check the GPU first: `oc describe node | grep -A3 nvidia.com/gpu` (how much VRAM decides the model size).
3. *Models* → **Deploy model** → serving runtime **vLLM NVIDIA GPU ServingRuntime for KServe**.
   - Model: `Qwen/Qwen2.5-7B-Instruct` (or `ibm-granite/granite-3.3-8b-instruct`) – from the model catalog / an OCI modelcar / S3 connection.
   - Deployment name: `qwen25-7b-instruct` (this becomes the served model name and the service name).
   - 1 GPU, *no* external route needed (the app calls it inside the cluster). Token auth: off for internal use, or put the token into `LLM_API_KEY`.
   - Additional runtime args:
     ```
     --max-model-len=16384
     --enable-auto-tool-choice
     --tool-call-parser=hermes        # Qwen; use "granite" for Granite
     ```
4. Test from inside the cluster:
   ```bash
   oc -n avida-models get inferenceservice
   oc -n avida-models run curl --rm -it --image=registry.access.redhat.com/ubi9/ubi -- \
     curl -s http://qwen25-7b-instruct-predictor.avida-models.svc.cluster.local:8080/v1/models
   ```
   If the port differs, check `oc -n avida-models get svc`.

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
