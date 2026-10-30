# DeepGeneLens

DeepGeneLens is a research-prototype AI genomic analysis platform. It provides
FASTA statistics, PDF reports, and an experimental viral-family 1D-CNN trained
from a real NCBI RefSeq snapshot. It is not a clinically validated diagnostic
system.

## Project structure

```text
DeepGeneLens/
├── backend/
│   ├── app/
│   │   ├── bioinformatics/
│   │   ├── explainability/
│   │   ├── models/
│   │   ├── reports/
│   │   ├── routes/
│   │   ├── config.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    ├── .env.example
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Run the backend

From `backend` in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs).

The upload endpoint `POST /api/uploads/fasta` accepts `.fasta`, `.fa`, and
`.fna` files up to 10 MB, parses their records, validates DNA characters, and
returns composition and GC statistics. `POST /api/uploads/report` creates a
downloadable PDF from those calculated statistics. Neither endpoint classifies
pathogens or makes clinical claims.

## Run the frontend

Install Node.js LTS first if `node` and `npm` are not available, then from `frontend`:

```powershell
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173/). The page checks `VITE_API_BASE_URL` (default `http://localhost:8000`) and displays the backend status.

Use the upload panel to send a FASTA file to the backend and view the complete
analysis results. The existing statistics and PDF workflow remain available.

## Train and use the experimental CNN

The prepared large snapshot is stored in `data/refseq_viral_large/`. It
contains 712 cleaned records from 12 taxonomy-derived viral families with
cluster-aware train/validation/test splits and no detected split overlap.
Train the model from the repository root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.models.train_cnn --dataset ..\data\refseq_viral_large --model ..\artifacts\viral_family_cnn.pt --max-length 4096 --epochs 12
```

The completed experimental checkpoint is
`artifacts/viral_family_cnn.pt`; metrics and training metadata are in
`artifacts/viral_family_cnn.metrics.json`. The measured held-out test
results are accuracy `0.6396`, weighted precision `0.6359`, weighted recall
`0.6396`, and weighted F1 `0.5975` on 111 sequences. These are research
metrics for this snapshot, not clinical performance or model accuracy claims.

`POST /api/analysis/predict` accepts `.fasta`, `.fa`, and `.fna` files and
returns one family prediction per valid sequence. The endpoint returns HTTP
503 when the checkpoint is absent and rejects invalid DNA instead of producing
fallback predictions. Set `MODEL_PATH` to override the checkpoint location.

## Current scope

Explainability, CNN-LSTM, DNABERT, authentication, analysis history, and
PostgreSQL remain future phases and are not represented as fabricated
functionality.

## RefSeq viral dataset pipeline

The first dataset pipeline is implemented in
`backend/app/datasets/refseq_viral.py`. It queries NCBI Entrez for RefSeq
viral complete-genome records, keeps DNA records with taxonomy-derived
`viridae` family labels, removes invalid and duplicate sequences, and creates
deterministic cluster-aware splits.

From the repository root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.datasets.refseq_viral --output ..\data\refseq_viral --max-records 500 --max-families 8 --per-family 20 --min-length 500
```

Generated artifacts are stored under `data/refseq_viral/`:

- `raw/refseq_viral_dna.fasta`
- `processed/train.csv`
- `processed/validation.csv`
- `processed/test.csv`
- `manifests/manifest.json`
- `manifests/class_distribution.csv`
- `manifests/split_leakage_report.json`

The generated snapshot and trained model are suitable only for a small
experimental 1D-CNN baseline. The lightweight 15-mer clustering heuristic is
not a substitute for full phylogenetic or ANI analysis, and the model
truncates sequences at 4,096 bases. Neither the dataset nor the model is
clinically validated.
