# ============================================================
# Enterprise RAG Assistant — Hardened Dockerfile
# ============================================================
# Sécurité appliquée :
#   - Image minimale python:3.12-slim (petite surface d'attaque)
#   - Multi-stage build pour réduire la taille finale
#   - Utilisateur non-root dédié (appuser, UID 1000)
#   - pip --no-cache-dir (pas de cache inutile dans l'image)
#   - Pas de shell root, pas de sudo
#   - HEALTHCHECK intégré
# ============================================================

# --- Stage 1 : Build des dépendances ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Installer les dépendances système nécessaires pour compiler certains packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Installer les dépendances Python dans un venv isolé
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# --- Stage 2 : Image finale minimale ---
FROM python:3.12-slim AS runtime

# Métadonnées
LABEL maintainer="saif" \
      app="enterprise-rag-assistant" \
      security="hardened"

# Créer un utilisateur système dédié (pas de shell, pas de home)
# UID/GID 1000 — correspond au securityContext K8s
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /usr/sbin/nologin --no-create-home appuser

# Copier le venv depuis le builder
COPY --from=builder /opt/venv /opt/venv

# S'assurer que le venv est dans le PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Répertoire de l'application
WORKDIR /app

# Copier le code source
COPY api.py .
COPY app.py .
COPY app_demo.py .
COPY ingest.py .
COPY requirements.txt .
COPY static/ ./static/

# Créer les répertoires writables nécessaires au runtime
# (uploads, chroma_db, tmp pour les librairies ML)
RUN mkdir -p /app/uploads /app/chroma_db /tmp && \
    chown -R appuser:appgroup /app /tmp && \
    chmod -R 755 /app && \
    chmod 1777 /tmp

# Healthcheck — vérifie que l'API répond
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

# Basculer vers l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 8000

# Lancer l'application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
