"""
Test conflict handling in parallel dance moves.

NOTE: This test requires CombineConflictError and set_dancer() methods
which are not yet implemented in the current system.

To re-enable, implement:
1. CombineConflictError exception class in DanceFloor
2. set_dancer() method in DanceFloor to place dancers at positions
3. Test data fixtures for collision scenarios
"""

import os
import json
import Dance
import DanceFloor as DF
from Dancer import Dancer

FIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'Figures')
FIG_DIR = os.path.abspath(FIG_DIR)


# DISABLED: Waiting for CombineConflictError implementation
# def test_parallel_conflict_raises():
#     pass
