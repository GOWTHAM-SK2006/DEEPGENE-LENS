"""Real model inference endpoint."""

from io import StringIO
from pathlib import Path
import os

import torch
from Bio import SeqIO
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.bioinformatics.fasta import FastaParseError, summarize_fasta
from app.models.cnn import DNA1DCNN, encode_sequence

router = APIRouter()


@router.post("/predict", tags=["analysis"])
async def predict(file: UploadFile = File(...)) -> dict[str, object]:
    """Run inference only when a trained compatible checkpoint is installed."""
    filename = file.filename or ""
    if not filename.lower().endswith((".fasta", ".fa", ".fna")):
        raise HTTPException(status_code=415, detail="Please upload a .fasta, .fa, or .fna file.")
    content = await file.read()
    try:
        analysis = summarize_fasta(content)
    except FastaParseError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not analysis["valid"]:
        raise HTTPException(status_code=422, detail="Prediction requires sequences containing only A, T, G, and C.")

    default_model_path = Path(__file__).resolve().parents[3] / "artifacts" / "viral_family_cnn.pt"
    model_path = Path(os.getenv("MODEL_PATH", str(default_model_path)))
    if not model_path.exists():
        raise HTTPException(status_code=503, detail="No trained model is installed. Prediction is unavailable.")
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    label_mapping = checkpoint["label_mapping"]
    model = DNA1DCNN(len(label_mapping))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    max_length = int(checkpoint["max_length"])
    records = list(SeqIO.parse(StringIO(content.decode("utf-8")), "fasta"))
    predictions = []
    with torch.no_grad():
        for record in records:
            probabilities = torch.softmax(
                model(encode_sequence(str(record.seq), max_length).unsqueeze(0)), dim=1
            )[0]
            confidence, index = probabilities.max(dim=0)
            family = next(label for label, value in label_mapping.items() if value == index.item())
            predictions.append({
                "sequence_id": record.id,
                "predicted_family": family,
                "confidence": round(confidence.item(), 4),
            })
    return {
        "filename": filename,
        "predictions": predictions,
        "model": checkpoint["metadata"],
        "research_only": True,
    }
