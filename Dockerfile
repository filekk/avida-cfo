# Single image: builds the Vue app, then serves it from FastAPI on :8080.
# OpenShift builds this automatically: oc new-app <repo-url> --strategy=docker

# --- 1) Frontend build --------------------------------------------------------
# Node 22 LTS (Node 20 reached end of life on 30 Apr 2026). `npm ci` installs exactly what package-lock.json pins.
FROM registry.access.redhat.com/ubi9/nodejs-22:latest AS frontend
WORKDIR /opt/app-root/src
COPY --chown=1001:0 frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY --chown=1001:0 frontend/ ./
RUN npm run build

# --- 2) Backend runtime -------------------------------------------------------
FROM registry.access.redhat.com/ubi9/python-311:latest
WORKDIR /opt/app-root/src
COPY --chown=1001:0 backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=1001:0 backend/ ./
COPY --from=frontend --chown=1001:0 /opt/app-root/src/dist ./static

# OpenShift runs with a random UID in group 0 – make files group-readable.
RUN chmod -R g=u /opt/app-root/src
USER 1001
ENV STATIC_DIR=/opt/app-root/src/static PYTHONUNBUFFERED=1
EXPOSE 8080
# PaaS hosts (Render, Railway, Koyeb, HF Spaces…) pass the port in $PORT; 8080 otherwise (OpenShift, compose).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
