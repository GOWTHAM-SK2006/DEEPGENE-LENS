"""Download and prepare a small, auditable NCBI RefSeq viral DNA dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from Bio import Entrez, SeqIO
from Bio.Seq import UndefinedSequenceError
from Bio.SeqRecord import SeqRecord


SEARCH_TERM = (
    'txid10239[Organism] AND refseq[filter] AND '
    '"complete genome"[Title]'
)
DEFAULT_MAX_RECORDS = 1500
DEFAULT_MAX_FAMILIES = 8
DEFAULT_PER_FAMILY = 25
DEFAULT_MIN_LENGTH = 500
KMER_SIZE = 15
SIMILARITY_THRESHOLD = 0.95


@dataclass
class GenomeRecord:
    accession: str
    family: str
    organism: str
    length: int
    sequence: str
    taxonomy: list[str]
    molecule_type: str


def prepare_dataset(
    output_root: Path,
    max_records: int = DEFAULT_MAX_RECORDS,
    max_families: int = DEFAULT_MAX_FAMILIES,
    per_family: int = DEFAULT_PER_FAMILY,
    min_length: int = DEFAULT_MIN_LENGTH,
    seed: int = 42,
) -> dict[str, object]:
    """Download, clean, deduplicate, split, and report a RefSeq snapshot."""
    output_root.mkdir(parents=True, exist_ok=True)
    raw_dir = output_root / "raw"
    processed_dir = output_root / "processed"
    manifest_dir = output_root / "manifests"
    for directory in (raw_dir, processed_dir, manifest_dir):
        directory.mkdir(parents=True, exist_ok=True)

    Entrez.email = os.getenv("NCBI_EMAIL", "deepgenelens@example.com")
    downloaded_at = datetime.now(timezone.utc).isoformat()
    ids = _search_ids(max_records)
    records, undefined_records = _fetch_records(ids)
    _write_raw_fasta(records, raw_dir / "refseq_viral_dna.fasta")

    cleaned, removal_counts = _clean_records(records, min_length)
    removal_counts["undefined_sequence"] = undefined_records
    selected = _select_families(cleaned, max_families, per_family)
    groups = _cluster_records(selected)
    splits = _split_by_family_and_group(selected, groups, seed)

    _write_split_files(processed_dir, splits)
    _write_class_distribution(manifest_dir / "class_distribution.csv", splits)
    leakage = _write_leakage_report(manifest_dir / "split_leakage_report.json", splits, groups)

    manifest = {
        "dataset_name": "NCBI RefSeq viral complete-genome DNA snapshot",
        "source": "NCBI Nucleotide/RefSeq via Entrez E-utilities",
        "source_url": "https://www.ncbi.nlm.nih.gov/refseq/",
        "search_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "query": SEARCH_TERM,
        "downloaded_at_utc": downloaded_at,
        "ncbi_email": Entrez.email,
        "license_notice": (
            "NCBI data may include records with source-specific terms. "
            "Review NCBI policies and original record attribution before redistribution."
        ),
        "ncbi_policy_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
        "parameters": {
            "max_records_requested": max_records,
            "max_families": max_families,
            "max_records_per_family": per_family,
            "minimum_length": min_length,
            "random_seed": seed,
            "kmer_size": KMER_SIZE,
            "similarity_threshold": SIMILARITY_THRESHOLD,
        },
        "counts": {
            "search_ids": len(ids),
            "fetched_records": len(records),
            "cleaned_records": len(cleaned),
            "selected_records": len(selected),
            "selected_families": len({record.family for record in selected}),
            "train_records": len(splits["train"]),
            "validation_records": len(splits["validation"]),
            "test_records": len(splits["test"]),
        },
        "removals": removal_counts,
        "families": sorted({record.family for record in selected}),
        "files": {},
        "leakage_check": leakage,
        "suitable_for_1d_cnn": _suitability(splits),
        "suitability_reason": _suitability_reason(splits),
    }
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest["files"][str(path.relative_to(output_root))] = _sha256(path)
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _search_ids(max_records: int) -> list[str]:
    handle = Entrez.esearch(
        db="nuccore",
        term=SEARCH_TERM,
        retmax=max_records,
        sort="relevance",
        retmode="xml",
    )
    try:
        result = Entrez.read(handle)
    finally:
        handle.close()
    return list(result["IdList"])


def _fetch_records(ids: list[str]) -> tuple[list[GenomeRecord], int]:
    records: list[GenomeRecord] = []
    undefined_records = 0
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        handle = Entrez.efetch(
            db="nuccore",
            id=",".join(batch),
            rettype="gb",
            retmode="text",
        )
        try:
            for record in SeqIO.parse(handle, "genbank"):
                parsed = _parse_record(record)
                if parsed is not None:
                    records.append(parsed)
                elif _has_undefined_sequence(record):
                    undefined_records += 1
        finally:
            handle.close()
        time.sleep(0.35)
    return records, undefined_records


def _parse_record(record: SeqRecord) -> GenomeRecord | None:
    try:
        sequence = str(record.seq).upper()
    except UndefinedSequenceError:
        return None
    molecule_type = str(record.annotations.get("molecule_type", ""))
    taxonomy = [str(item) for item in record.annotations.get("taxonomy", [])]
    family = next((item for item in reversed(taxonomy) if item.lower().endswith("viridae")), None)
    if not family or molecule_type.upper() != "DNA":
        return None
    accession = str(record.annotations.get("accessions", [record.id])[0])
    organism = str(record.annotations.get("organism", ""))
    return GenomeRecord(
        accession=accession,
        family=family,
        organism=organism,
        length=len(sequence),
        sequence=sequence,
        taxonomy=taxonomy,
        molecule_type=molecule_type,
    )


def _has_undefined_sequence(record: SeqRecord) -> bool:
    try:
        str(record.seq)
    except UndefinedSequenceError:
        return True
    return False


def _clean_records(
    records: Iterable[GenomeRecord],
    min_length: int,
) -> tuple[list[GenomeRecord], dict[str, int]]:
    removals = Counter()
    seen_accessions: set[str] = set()
    seen_sequences: set[str] = set()
    cleaned: list[GenomeRecord] = []
    for record in records:
        if record.length < min_length:
            removals["below_minimum_length"] += 1
            continue
        if not record.sequence or any(base not in "ATGC" for base in record.sequence):
            removals["invalid_dna"] += 1
            continue
        if record.accession in seen_accessions:
            removals["duplicate_accession"] += 1
            continue
        if record.sequence in seen_sequences:
            removals["duplicate_sequence"] += 1
            continue
        seen_accessions.add(record.accession)
        seen_sequences.add(record.sequence)
        cleaned.append(record)
    return cleaned, dict(removals)


def _select_families(
    records: list[GenomeRecord],
    max_families: int,
    per_family: int,
) -> list[GenomeRecord]:
    by_family: dict[str, list[GenomeRecord]] = defaultdict(list)
    for record in records:
        by_family[record.family].append(record)
    eligible = sorted(
        ((family, values) for family, values in by_family.items() if len(values) >= 3),
        key=lambda item: (-len(item[1]), item[0]),
    )[:max_families]
    selected: list[GenomeRecord] = []
    for _, values in eligible:
        selected.extend(sorted(values, key=lambda record: record.accession)[:per_family])
    return selected


def _cluster_records(records: list[GenomeRecord]) -> dict[str, str]:
    """Group exact and very-near duplicate genomes before splitting."""
    parent = {record.accession: record.accession for record in records}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    for index, first in enumerate(records):
        first_kmers = _kmers(first.sequence)
        for second in records[index + 1:]:
            if min(first.length, second.length) / max(first.length, second.length) < 0.95:
                continue
            second_kmers = _kmers(second.sequence)
            union_size = len(first_kmers | second_kmers)
            similarity = len(first_kmers & second_kmers) / union_size if union_size else 0
            if similarity >= SIMILARITY_THRESHOLD:
                union(first.accession, second.accession)
    return {accession: find(accession) for accession in parent}


def _kmers(sequence: str) -> set[str]:
    return {sequence[index:index + KMER_SIZE] for index in range(len(sequence) - KMER_SIZE + 1)}


def _split_by_family_and_group(
    records: list[GenomeRecord],
    groups: dict[str, str],
    seed: int,
) -> dict[str, list[GenomeRecord]]:
    randomizer = random.Random(seed)
    by_family: dict[str, list[GenomeRecord]] = defaultdict(list)
    for record in records:
        by_family[record.family].append(record)
    result = {"train": [], "validation": [], "test": []}
    for family, family_records in sorted(by_family.items()):
        by_group: dict[str, list[GenomeRecord]] = defaultdict(list)
        for record in family_records:
            by_group[groups[record.accession]].append(record)
        family_groups = list(by_group.values())
        randomizer.shuffle(family_groups)
        if len(family_groups) < 3:
            continue
        test_count = max(1, round(len(family_groups) * 0.15))
        validation_count = max(1, round(len(family_groups) * 0.15))
        result["test"].extend(record for group in family_groups[:test_count] for record in group)
        result["validation"].extend(
            record for group in family_groups[test_count:test_count + validation_count] for record in group
        )
        result["train"].extend(
            record for group in family_groups[test_count + validation_count:] for record in group
        )
    return result


def _write_raw_fasta(records: list[GenomeRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(f">{record.accession}|family={record.family}|organism={record.organism}\n")
            for index in range(0, len(record.sequence), 80):
                handle.write(record.sequence[index:index + 80] + "\n")


def _write_split_files(output_dir: Path, splits: dict[str, list[GenomeRecord]]) -> None:
    fields = ["accession", "family", "organism", "length", "sequence"]
    for split_name, records in splits.items():
        with (output_dir / f"{split_name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for record in sorted(records, key=lambda item: item.accession):
                writer.writerow({field: getattr(record, field) for field in fields})


def _write_class_distribution(path: Path, splits: dict[str, list[GenomeRecord]]) -> None:
    families = sorted({record.family for records in splits.values() for record in records})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["family", "train", "validation", "test", "total"])
        for family in families:
            counts = [sum(record.family == family for record in splits[name]) for name in ("train", "validation", "test")]
            writer.writerow([family, *counts, sum(counts)])


def _write_leakage_report(
    path: Path,
    splits: dict[str, list[GenomeRecord]],
    groups: dict[str, str],
) -> dict[str, object]:
    split_groups = {name: {groups[record.accession] for record in records} for name, records in splits.items()}
    overlap = {
        f"{first}_{second}": sorted(split_groups[first] & split_groups[second])
        for first, second in (("train", "validation"), ("train", "test"), ("validation", "test"))
    }
    report = {
        "cluster_method": f"{KMER_SIZE}-mer Jaccard similarity >= {SIMILARITY_THRESHOLD}",
        "cluster_count": len(set(groups.values())),
        "split_group_counts": {name: len(value) for name, value in split_groups.items()},
        "overlap_counts": {name: len(value) for name, value in overlap.items()},
        "leakage_free": all(not value for value in overlap.values()),
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _suitability(splits: dict[str, list[GenomeRecord]]) -> bool:
    families = {record.family for records in splits.values() for record in records}
    return bool(families) and all(splits[name] for name in ("train", "validation", "test"))


def _suitability_reason(splits: dict[str, list[GenomeRecord]]) -> str:
    if not _suitability(splits):
        return "Not suitable: one or more required splits are empty."
    return "Suitable for a small experimental 1D-CNN baseline; not clinically validated."


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/refseq_viral"))
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS)
    parser.add_argument("--max-families", type=int, default=DEFAULT_MAX_FAMILIES)
    parser.add_argument("--per-family", type=int, default=DEFAULT_PER_FAMILY)
    parser.add_argument("--min-length", type=int, default=DEFAULT_MIN_LENGTH)
    args = parser.parse_args()
    manifest = prepare_dataset(
        args.output,
        args.max_records,
        args.max_families,
        args.per_family,
        args.min_length,
    )
    print(json.dumps(manifest["counts"], indent=2))
    print(f"suitable_for_1d_cnn={manifest['suitable_for_1d_cnn']}")
    print(manifest["suitability_reason"])


if __name__ == "__main__":
    main()
