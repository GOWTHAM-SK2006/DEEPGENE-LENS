"""FASTA upload endpoints."""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.bioinformatics.fasta import FastaParseError, summarize_fasta
from app.reports.pdf import build_analysis_pdf

router = APIRouter()


@router.post("/fasta", status_code=status.HTTP_200_OK, tags=["uploads"])
async def upload_fasta(file: UploadFile = File(...)) -> dict[str, object]:
    """Parse an uploaded FASTA file without running a prediction."""
    filename = file.filename or ""
    if not filename.lower().endswith((".fasta", ".fa", ".fna")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a .fasta, .fa, or .fna file.",
        )

    content = await file.read()
    try:
        summary = summarize_fasta(content)
    except FastaParseError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return {
        "filename": filename,
        "message": "FASTA file uploaded and parsed successfully.",
        "analysis_ready": True,
        **summary,
    }


@router.post("/report", tags=["reports"])
async def download_report(
    file: UploadFile = File(...),
    predictions_json: str | None = Form(default=None),
    model_metadata_json: str | None = Form(default=None),
) -> StreamingResponse:
    """Create a PDF report from calculated FASTA statistics."""
    filename = file.filename or ""
    if not filename.lower().endswith((".fasta", ".fa", ".fna")):
        raise HTTPException(status_code=415, detail="Please upload a .fasta, .fa, or .fna file.")
    try:
        analysis = summarize_fasta(await file.read())
    except FastaParseError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        predictions = json.loads(predictions_json) if predictions_json else None
        model_metadata = json.loads(model_metadata_json) if model_metadata_json else None
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=422, detail="Prediction metadata is not valid JSON.") from error
    if predictions is not None and not isinstance(predictions, list):
        raise HTTPException(status_code=422, detail="Prediction metadata must be a list.")
    if model_metadata is not None and not isinstance(model_metadata, dict):
        raise HTTPException(status_code=422, detail="Model metadata must be an object.")

    return StreamingResponse(
        build_analysis_pdf(filename, analysis, predictions, model_metadata),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="deepgenelens-analysis.pdf"'},
    )
