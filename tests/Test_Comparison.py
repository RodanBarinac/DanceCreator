"""
Comparison Test: New vs Old System
Compares the new DanceCreator with the Archive version.
Tests:
  - showCrips() output (Figure crisp descriptions)
  - Final DanceFloor print() output
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Change working directory to project root so relative paths work
os.chdir(str(PROJECT_ROOT))

# Import new system
import Dance as NewDance
import DanceFloor as NewDF

# Import old system from Archive using importlib to avoid naming conflicts
import importlib.util

old_dance_spec = importlib.util.spec_from_file_location("OldDance", str(PROJECT_ROOT / 'Archive' / 'Dance.py'))
OldDance = importlib.util.module_from_spec(old_dance_spec)
old_dance_spec.loader.exec_module(OldDance)

old_df_spec = importlib.util.spec_from_file_location("OldDF", str(PROJECT_ROOT / 'Archive' / 'DanceFloor.py'))
OldDF = importlib.util.module_from_spec(old_df_spec)
old_df_spec.loader.exec_module(OldDF)


def run_new_system(dance_name: str, num_couples: int) -> tuple:
    """Run comparison using NEW system."""
    print("\n" + "="*60)
    print("NEW SYSTEM")
    print("="*60)
    
    floor = NewDF.DanceFloor(dance_name, num_couples)
    print("\n--- Initial DanceFloor ---")
    print(floor)
    
    dance = NewDance.getDance(dance_name)
    print("\n--- ShowCrips Output ---")
    crips = NewDance.showCrips(dance, floor)
    
    print("\n--- Final DanceFloor ---")
    final_floor = dance.DanceMove(floor)
    print(final_floor)
    
    return crips, final_floor


def run_old_system(dance_name: str, num_couples: int) -> tuple:
    """Run comparison using OLD system from Archive."""
    print("\n" + "="*60)
    print("OLD SYSTEM (Archive)")
    print("="*60)
    
    floor = OldDF.DanceFloor(dance_name, num_couples)
    print("\n--- Initial DanceFloor ---")
    print(floor)
    
    dance = OldDance.getDance(dance_name)
    print("\n--- ShowCrips Output ---")
    crips = OldDance.showCrips(dance, floor)
    
    print("\n--- Final DanceFloor ---")
    final_floor = dance.DanceMove(floor)
    print(final_floor)
    
    return crips, final_floor


def compare_systems(dance_name: str, num_couples: int):
    """Compare outputs from both systems."""
    print("\n" + "#"*60)
    print(f"# COMPARISON: {dance_name} ({num_couples} couples)")
    print("#"*60)
    
    try:
        new_crips, new_floor = run_new_system(dance_name, num_couples)
    except Exception as e:
        print(f"ERROR in new system: {e}")
        new_crips, new_floor = None, None
    
    try:
        old_crips, old_floor = run_old_system(dance_name, num_couples)
    except Exception as e:
        print(f"ERROR in old system: {e}")
        old_crips, old_floor = None, None
    
    # Comparison summary
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    if new_crips and old_crips:
        crips_match = str(new_crips) == str(old_crips)
        print(f"Crips match: {crips_match}")
    
    if new_floor and old_floor:
        floor_match = str(new_floor) == str(old_floor)
        print(f"Final Floor match: {floor_match}")


if __name__ == "__main__":
    # Run comparison
    compare_systems("Marries Wedding_all", 3)