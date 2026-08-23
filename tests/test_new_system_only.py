"""
Simple test: Shows Crips and DanceFloor for Marries Wedding (NEW system only)
"""
import sys
import os
from pathlib import Path

# Set working directory to project root
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Import new system
import Dance
import DanceFloor as DF

if __name__ == "__main__":
    print("="*60)
    print("MARRIES WEDDING - NEW SYSTEM")
    print("="*60)
    
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
        sys.exit(1)
    
    # Show crips
    print("\n3. ShowCrips Output:")
    print("-"*60)
    try:
        crips = Dance.showCrips(dance, floor)
        print(f"   Crips returned: {type(crips)}")
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
