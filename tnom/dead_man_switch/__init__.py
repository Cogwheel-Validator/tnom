"""Health check module.

This package provides functions for triggering a dead man switch.
"""

from .health_check import dead_man_switch_trigger, run_health_check

__all__ = ["run_health_check", "dead_man_switch_trigger"]
