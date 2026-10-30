"""Train and evaluate the experimental viral-family 1D-CNN."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, Dataset

from app.models.cnn import DNA1DCNN, encode_sequence, save_checkpoint

csv.field_size_limit(50_000_000)


class SequenceDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, path: Path, label_mapping: dict[str, int], max_length: int) -> None:
        with path.open(encoding="utf-8") as handle:
            self.rows = list(csv.DictReader(handle))
        self.label_mapping = label_mapping
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        return encode_sequence(row["sequence"], self.max_length), torch.tensor(
            self.label_mapping[row["family"]], dtype=torch.long
        )


def train_model(
    dataset_root: Path,
    model_path: Path,
    max_length: int = 4096,
    epochs: int = 12,
    batch_size: int = 8,
    learning_rate: float = 0.001,
    seed: int = 42,
) -> dict[str, object]:
    """Train only from the prepared dataset split files."""
    _seed_everything(seed)
    processed = dataset_root / "processed"
    with (processed / "train.csv").open(encoding="utf-8") as handle:
        train_rows = list(csv.DictReader(handle))
    families = sorted({row["family"] for row in train_rows})
    if len(families) < 2:
        raise ValueError("At least two training families are required.")
    label_mapping = {family: index for index, family in enumerate(families)}

    train_data = SequenceDataset(processed / "train.csv", label_mapping, max_length)
    validation_data = SequenceDataset(processed / "validation.csv", label_mapping, max_length)
    test_data = SequenceDataset(processed / "test.csv", label_mapping, max_length)
    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    validation_loader = DataLoader(validation_data, batch_size=batch_size)
    test_loader = DataLoader(test_data, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DNA1DCNN(len(label_mapping)).to(device)
    counts = Counter(row["family"] for row in train_rows)
    weights = torch.tensor(
        [len(train_rows) / (len(families) * counts[family]) for family in families],
        dtype=torch.float32,
        device=device,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss(weight=weights)
    history: list[dict[str, float]] = []
    best_validation_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            loss = criterion(model(inputs), targets)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(targets)
        validation_loss = _evaluate_loss(model, validation_loader, criterion, device)
        train_loss /= max(len(train_data), 1)
        validation_loss /= max(len(validation_data), 1)
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "validation_loss": validation_loss})
        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("Training did not produce a model checkpoint.")
    model.load_state_dict(best_state)
    metrics = _evaluate_metrics(model, test_loader, device, families)
    metadata = {
        "model_type": "PyTorch DNA 1D-CNN",
        "device": str(device),
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "max_length": max_length,
        "seed": seed,
        "class_count": len(families),
        "label_mapping": label_mapping,
        "history": history,
        "test_metrics": metrics,
        "research_only": True,
    }
    save_checkpoint(model_path, model, label_mapping, max_length, metadata)
    model_path.with_suffix(".metrics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def _evaluate_loss(model: DNA1DCNN, loader: DataLoader, criterion: nn.Module, device: torch.device) -> float:
    model.eval()
    total = 0.0
    with torch.no_grad():
        for inputs, targets in loader:
            total += criterion(model(inputs.to(device)), targets.to(device)).item() * len(targets)
    return total


def _evaluate_metrics(
    model: DNA1DCNN,
    loader: DataLoader,
    device: torch.device,
    families: list[str],
) -> dict[str, object]:
    model.eval()
    actual: list[int] = []
    predicted: list[int] = []
    with torch.no_grad():
        for inputs, targets in loader:
            predicted.extend(model(inputs.to(device)).argmax(dim=1).cpu().tolist())
            actual.extend(targets.tolist())
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual, predicted, labels=list(range(len(families))), average="weighted", zero_division=0
    )
    return {
        "accuracy": accuracy_score(actual, predicted),
        "precision_weighted": precision,
        "recall_weighted": recall,
        "f1_weighted": f1,
        "confusion_matrix": confusion_matrix(actual, predicted, labels=list(range(len(families)))).tolist(),
        "classification_report": classification_report(
            actual, predicted, labels=list(range(len(families))), target_names=families, zero_division=0, output_dict=True
        ),
    }


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/refseq_viral_large"))
    parser.add_argument("--model", type=Path, default=Path("artifacts/viral_family_cnn.pt"))
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args()
    result = train_model(args.dataset, args.model, args.max_length, args.epochs)
    print(json.dumps(result["test_metrics"], indent=2))


if __name__ == "__main__":
    main()
