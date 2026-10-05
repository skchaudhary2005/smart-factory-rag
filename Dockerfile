FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY src ./src
COPY tests ./tests
COPY models ./models

RUN pip install --no-cache-dir setuptools hatchling
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --no-cache-dir --no-build-isolation . --no-deps
RUN pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "pydantic-ai>=1.0,<2" "pydantic>=2.7,<3" "python-dotenv>=1.0,<2" "sentence-transformers>=3.0" "faiss-cpu>=1.8.0" "rank-bm25>=0.2.2" "lightgbm>=4.3.0" "numpy>=1.26.0" "pandas>=2.2.0" "aiomqtt>=2.0.0" "paho-mqtt>=2.1.0" "pypdf>=4.0.0" "python-docx>=1.1.0" "openpyxl>=3.1.0" "joblib>=1.3.0" "structlog>=24.0.0" "pyyaml>=6.0" "psycopg[binary]"

# Git LFS files may arrive as pointer files in Render Docker build contexts.
# Download the real industrial model artifact when that happens.
RUN python - <<'PY'
from pathlib import Path
import urllib.request

p = Path("/app/models/industrial/failure_model.joblib")
if p.exists() and p.read_text(errors="ignore").startswith("version https://git-lfs.github.com/spec/v1"):
    url = "https://github.com/skchaudhary2005/smart-factory-rag/raw/main/models/industrial/failure_model.joblib"
    tmp = p.with_suffix(".joblib.download")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(p)
print("industrial model bytes:", p.stat().st_size if p.exists() else 0)
PY

EXPOSE 8000

CMD ["uvicorn","src.api.main:app","--host","0.0.0.0","--port","8000"]
