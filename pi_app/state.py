"""pi_app/state.py
Simple shared state for Pi threads.
"""

from dataclasses import dataclass


@dataclass
class SystemState:
    streaming: bool = False
    running: bool = True
