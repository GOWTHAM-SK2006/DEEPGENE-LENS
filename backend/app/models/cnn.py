"""Shared DNA encoder and PyTorch 1D-CNN classifier."""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn


BASES = "ACGT"
BASE_TO_INDEX = {base: index for index, base in enumerate(BASES)}


def encode_sequence(sequence: str, max_length: int) -> torch.Tensor:
    """Encode DNA as a [channels, length] one-hot tensor."""
    encoded = torch.zeros((len(BASES), max_length), dtype=torch.float32)
    for position, base in enumerate(sequence.upper()[:max_length]):
        index = BASE_TO_INDEX.get(base)
        if index is not None:
            encoded[index, position] = 1.0
    return encoded


class DNA1DCNN(nn.Module):
    """Compact 1D-CNN for experimental viral-family classification."""

    def __init__(self, class_count: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(4, 32, kernel_size=11, padding=5),
            nn.ReLU(),
            nn.MaxPool1d(4),
            nn.Conv1d(32, 64, kernel_size=9, padding=4),
            nn.ReLU(),
            nn.MaxPool1d(4),
            nn.Conv1d(64, 128, kernel_size=7, padding=3),
            nn.ReLU(),
            nn.AdaptiveMaxPool1d(1),
        )
        self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.25), nn.Linear(128, class_count))

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(inputs))


def save_checkpoint(
    path: Path,
    model: DNA1DCNN,
    label_mapping: dict[str, int],
    max_length: int,
    metadata: dict[str, object],
) -> None:
    """Save model weights and the exact preprocessing contract."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "label_mapping": label_mapping,
            "max_length": max_length,
            "metadata": metadata,
        },
        path,
    )
