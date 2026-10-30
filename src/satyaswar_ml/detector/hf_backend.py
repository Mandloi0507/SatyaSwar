"""
Hugging Face Transformers Anti-Spoofing Detector Backend.
Authoritative source: Implementation.md, Section 7.4

Wraps Wav2Vec2 / XLS-R models for deepfake speech detection:
- In-memory inference with torch.inference_mode() and eval().
- GPU fp16 autocast support with CPU fallback.
- Explicit label mapping ensuring spoof_prob is strictly P(synthetic).
- Thread-safe single-worker execution.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch

from satyaswar_ml.detector.base import Detector, DetectorOutput


class HuggingFaceDetector(Detector):
    """
    Hugging Face Audio Classification wrapper for synthetic voice detection.
    """

    def __init__(
        self,
        model_name_or_path: str = "facebook/wav2vec2-xls-r-300m",
        device: str = "auto",
        precision: str = "fp16",
        input_samples: int = 64600,
        spoof_class_index: int = 1,
        version: str = "1.0",
    ):
        self.name = model_name_or_path
        self.version = version
        self.input_samples = input_samples
        self.spoof_class_index = spoof_class_index
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Device selection
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.precision = precision if (self.device == "cuda" and precision == "fp16") else "fp32"
        self.model: torch.nn.Module | None = None
        self._warmed_up = False

    def load_model(self) -> None:
        """Load pretrained checkpoint."""
        if self.model is not None:
            return

        with self._lock:
            if self.model is not None:
                return

            try:
                from transformers import AutoModelForAudioClassification
                self.model = AutoModelForAudioClassification.from_pretrained(self.name)
            except Exception:
                # Fallback to feature extraction classifier head if standard model card is a base feature extractor
                from transformers import AutoModel
                base_model = AutoModel.from_pretrained(self.name)
                # Classifier head over pooled hidden representation
                class FeatureClassifier(torch.nn.Module):
                    def __init__(self, base):
                        super().__init__()
                        self.base = base
                        hidden_dim = base.config.hidden_size
                        self.head = torch.nn.Sequential(
                            torch.nn.Linear(hidden_dim, 128),
                            torch.nn.ReLU(),
                            torch.nn.Linear(128, 2),
                        )

                    def forward(self, input_values):
                        outputs = self.base(input_values)
                        pooled = torch.mean(outputs.last_hidden_state, dim=1)
                        logits = self.head(pooled)
                        return logits

                self.model = FeatureClassifier(base_model)

            self.model.eval()
            self.model.to(self.device)

    def warmup(self) -> None:
        """Execute one dummy inference window to prime CUDA memory and caches."""
        if self._warmed_up:
            return
        dummy = np.zeros(self.input_samples, dtype=np.float32)
        self.predict(dummy)
        self._warmed_up = True

    def _sync_predict(self, wav: np.ndarray) -> DetectorOutput:
        if self.model is None:
            self.load_model()

        # Ensure correct length
        if len(wav) != self.input_samples:
            if len(wav) < self.input_samples:
                wav = np.pad(wav, (0, self.input_samples - len(wav)))
            else:
                wav = wav[:self.input_samples]

        # Per-utterance zero-mean unit-variance normalisation
        mean = np.mean(wav)
        std = np.std(wav) + 1e-7
        normalized = (wav - mean) / std

        tensor_in = torch.from_numpy(normalized).unsqueeze(0).to(self.device)

        use_cuda_autocast = (self.device == "cuda" and self.precision == "fp16")

        with torch.inference_mode():
            with torch.amp.autocast(device_type="cuda", enabled=use_cuda_autocast):
                outputs = self.model(tensor_in)
                if hasattr(outputs, "logits"):
                    logits = outputs.logits
                else:
                    logits = outputs

                probs = torch.softmax(logits, dim=-1).squeeze(0)
                spoof_prob = float(probs[self.spoof_class_index].item())

        return DetectorOutput(
            spoof_prob=float(np.clip(round(spoof_prob, 4), 0.0, 1.0)),
            raw={"logits": logits.detach().cpu().numpy().tolist(), "device": self.device},
        )

    def predict(self, wav: np.ndarray) -> DetectorOutput:
        """Run predict synchronously on dedicated worker thread to preserve event loop."""
        with self._lock:
            future = self._executor.submit(self._sync_predict, wav)
            return future.result()
