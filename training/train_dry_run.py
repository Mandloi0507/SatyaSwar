"""
Dry-run training validation script for SatyaSwar ML.
Authoritative source: Implementation.md, Section 10.2 & M10 Acceptance Criterion:
"Acceptance: a dry run on a 20-clip toy manifest completes end to end."
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.augment import augment_audio_clip
from training.prepare_data import generate_synthetic_manifest


class ToyDataset(Dataset):
    def __init__(self, manifest: list[dict]):
        self.manifest = manifest

    def __len__(self):
        return len(self.manifest)

    def __getitem__(self, idx):
        item = self.manifest[idx]
        # Generate simulated 4s audio (64,600 samples)
        audio = np.random.randn(64600).astype(np.float32) * 0.1
        # Apply augmentation if specified in manifest
        if item.get("codec") and item["codec"] != "clean":
            audio = augment_audio_clip(audio, codec_profile=item["codec"])
        label = int(item["label"])
        return torch.from_numpy(audio), torch.tensor(label, dtype=torch.long)


class SimpleAASISTHead(nn.Module):
    """Toy classifier head for dry-run validation."""
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv1d(1, 16, kernel_size=128, stride=64)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(16, 2)

    def forward(self, x):
        # x: [B, 64600] -> [B, 1, 64600]
        x = x.unsqueeze(1)
        h = torch.relu(self.conv(x))
        pooled = self.pool(h).squeeze(-1)
        return self.fc(pooled)


def run_dry_run_training(n_clips: int = 20) -> bool:
    print(f"Starting dry-run training validation on {n_clips}-clip toy manifest...")
    manifest = generate_synthetic_manifest(n_samples=n_clips)
    dataset = ToyDataset(manifest)
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)

    model = SimpleAASISTHead()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    model.train()
    total_loss = 0.0
    for step, (batch_x, batch_y) in enumerate(dataloader):
        optimizer.zero_grad()
        logits = model(batch_x)
        loss = criterion(logits, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    avg_loss = total_loss / len(dataloader)
    print(f"Dry-run training completed successfully! Avg loss over {len(dataloader)} batches: {avg_loss:.4f}")
    return True


if __name__ == "__main__":
    success = run_dry_run_training(n_clips=20)
    assert success
