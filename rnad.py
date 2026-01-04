"""
Compatibility shim for RNAD checkpoints.

The provided RNAD pickles reference the module name `rnad` and expect classes
like `RNaDSolver`, `RNaDConfig`, `StateRepresentation`, `NerdConfig`, etc.

This module attempts to import the full RNAD implementation from the checkpoints
directory. If that fails (e.g., missing JAX/Haiku dependencies), it falls back
to stub classes that allow unpickling but use a uniform random policy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Try to import the full RNAD module from the checkpoints directory
_FULL_RNAD_AVAILABLE = False
try:
    from scenarios.bargaining.rl_agent_checkpoints.rnad.rnad import (
        EntropySchedule,
        FineTuning,
        AdamConfig,
        NerdConfig,
        StateRepresentation,
        RNaDConfig,
        EnvStep,
        ActorStep,
        TimeStep,
        RNaDSolver,
    )
    _FULL_RNAD_AVAILABLE = True
    logger.debug("Full RNAD module loaded from checkpoints directory")
except ImportError as e:
    logger.warning(f"Full RNAD module not available ({e}); using fallback stubs")


# Fallback stub classes if full module is not available
if not _FULL_RNAD_AVAILABLE:

    class EntropySchedule:
        """Stub for EntropySchedule."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class FineTuning:
        """Stub for FineTuning."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class AdamConfig:
        """Stub for AdamConfig."""
        def __init__(self, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class NerdConfig:
        """Stub for NerdConfig."""
        beta: float = 2.0
        clip: float = 10_000

        def __init__(self, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class StateRepresentation:
        """Stub for StateRepresentation enum."""
        INFO_SET = "info_set"
        OBSERVATION = "observation"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            if args:
                self.value = args[0]
            self.__dict__.update(kwargs)

    class RNaDConfig:
        """Stub for RNaDConfig."""
        def __init__(self, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class EnvStep:
        """Stub for EnvStep."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class ActorStep:
        """Stub for ActorStep."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class TimeStep:
        """Stub for TimeStep."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    class RNaDSolver:
        """Stub RNaDSolver that uses uniform random policy as fallback."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._initialized = True
            self._fallback_warned = False
            self.__dict__.update(kwargs)

        def __setstate__(self, state: Dict[str, Any]) -> None:
            self.__dict__.update(state)
            self._fallback_warned = False

        def action_probabilities(self, state) -> Dict[int, float]:
            """Fallback policy: uniform over legal actions."""
            try:
                legal = list(state.legal_actions())
            except Exception:
                legal = []
            if not legal:
                return {}
            if not self._fallback_warned:
                logger.warning(
                    "RNAD fallback policy in use (uniform over legal actions); "
                    "original rnad module not available."
                )
                self._fallback_warned = True
            p = 1.0 / len(legal)
            return {int(a): p for a in legal}
