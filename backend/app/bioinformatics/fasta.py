"""FASTA parsing helpers for uploaded research data."""

from io import StringIO

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord


MAX_FASTA_BYTES = 10 * 1024 * 1024


class FastaParseError(ValueError):
    """Raised when an uploaded file is not a usable FASTA document."""


def summarize_fasta(content: bytes) -> dict[str, object]:
    """Parse FASTA bytes and return non-diagnostic sequence metadata."""
    if not content:
        raise FastaParseError("The uploaded file is empty.")
    if len(content) > MAX_FASTA_BYTES:
        raise FastaParseError("The uploaded file exceeds the 10 MB limit.")

    try:
        records = list(SeqIO.parse(StringIO(content.decode("utf-8")), "fasta"))
    except (UnicodeDecodeError, ValueError) as error:
        raise FastaParseError("The uploaded file could not be parsed as FASTA.") from error

    if not records:
        raise FastaParseError("No FASTA records were found in the uploaded file.")

    records_data = [_record_summary(record) for record in records]
    total_bases = sum(item["length"] for item in records_data)
    nucleotide_counts = {base: 0 for base in "ATGC"}
    invalid_bases = 0
    for record in records:
        for base in str(record.seq).upper():
            if base in nucleotide_counts:
                nucleotide_counts[base] += 1
            else:
                invalid_bases += 1

    composition = {
        base: _percentage(count, total_bases)
        for base, count in nucleotide_counts.items()
    }
    gc_content = _percentage(nucleotide_counts["G"] + nucleotide_counts["C"], total_bases)

    return {
        "sequence_count": len(records),
        "total_bases": total_bases,
        "valid": invalid_bases == 0,
        "invalid_base_count": invalid_bases,
        "composition": composition,
        "gc_content": gc_content,
        "records": records_data,
    }


def _record_summary(record: SeqRecord) -> dict[str, object]:
    sequence = str(record.seq).upper()
    length = len(sequence)
    gc_count = sequence.count("G") + sequence.count("C")
    return {
        "id": record.id,
        "description": record.description,
        "length": length,
        "gc_content": _percentage(gc_count, length),
    }


def _percentage(value: int, total: int) -> float:
    return round((value / total) * 100, 2) if total else 0.0
