"""Provider boundary for a future reviewed Runway adapter.

A production adapter must reserve the full CAD estimate before submission,
use idempotency, poll tasks, validate downloaded media, and reconcile actual
charges. Pricing, exchange rate and retry allowances must be explicit.
"""
from decimal import Decimal
from pathlib import Path
from typing import Protocol
from .core import Character, Scene, check_budget

class VideoProvider(Protocol):
    def estimate_cad(self, scene: Scene) -> Decimal: ...
    def generate(self, scene: Scene, characters: tuple[Character, ...], destination: Path) -> Path: ...

class RunwayProvider:
    """Disabled integration seam: cannot accidentally spend API credits."""
    def estimate_cad(self, scene: Scene) -> Decimal:
        raise NotImplementedError('Runway pricing and CAD conversion require configuration.')

    def generate(self, scene: Scene, characters: tuple[Character, ...], destination: Path) -> Path:
        raise NotImplementedError('Paid Runway generation is disabled in this initial mock release.')


def authorize_episode(provider: VideoProvider, scenes: tuple[Scene, ...], spent_cad=Decimal('0')) -> Decimal:
    # Validate each estimate too, so negative quotes cannot cancel valid charges.
    estimates = [check_budget(provider.estimate_cad(scene)) for scene in scenes]
    return check_budget(sum(estimates, Decimal('0')), spent_cad)
