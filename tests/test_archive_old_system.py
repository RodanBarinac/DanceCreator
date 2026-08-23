"""
Test: Shows Crips and DanceFloor for Marries Wedding (OLD system - run from Archive/)
"""
import sys
import os
from pathlib import Path

# Set working directory to project root so Dances/ and Figures/ paths work
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(str(PROJECT_ROOT))

# Add Archive to path
sys.path.insert(0, str(PROJECT_ROOT / 'Archive'))

# Import from Archive (in this context)
import Dance
import DanceFloor as DF

if __name__ == "__main__":
    print("============================================================")
    print("MARRIES WEDDING - OLD SYSTEM (Archive)")
    print("============================================================")
    
    # Create floor
    print("\n1. Creating DanceFloor (3 couples)...")
    floor = DF.DanceFloor("Marries Wedding", 3)
    print("\nInitial Floor:")
    print(floor)
    
    # Load dance
    print("\n2. Loading Dance: 'Marries Wedding_all'...")
    try:
        dance = Dance.getDance("Marries Wedding_all")
        print("   [OK] Dance loaded successfully")
    except Exception as e:
        print(f"   [ERROR] loading dance: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show crips
    print("\n3. ShowCrips Output:")
    print("-"*60)
    try:
        Dance.showCrips(dance, floor)
        print("   [OK] ShowCrips executed")
    except Exception as e:
        print(f"   [ERROR] in showCrips: {e}")
        import traceback
        traceback.print_exc()
    
    # Execute dance moves
    print("\n4. Executing DanceMove...")
    try:
        final_floor = dance.DanceMove(floor)
        print("   [OK] DanceMove executed")
    except Exception as e:
        print(f"   [ERROR] in DanceMove: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show final floor
    print("\n5. Final DanceFloor:")
    print("-"*60)
    print(final_floor)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
