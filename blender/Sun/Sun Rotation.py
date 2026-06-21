"""
Sun Rotation
============
Blender 5.0
Animates the Sun's rotation with its accurate physical parameters:
  - Axial tilt: 7.25 degrees relative to the ecliptic normal.
  - Rotation period: 25.05 days (sidereal period at the equator).
  - Synced to the Orrery timeline calibration: BASE_FRAMES = 300 frames per Earth year.
"""

import bpy
import math

# Orrery timeline calibration (300 frames = 1 Earth year of 365.25 days)
BASE_FRAMES = 300
EARTH_YEAR_DAYS = 365.25

# Physical Sun parameters
SUN_TILT_DEG = 7.25  # Axial tilt relative to ecliptic normal
SUN_ROTATION_DAYS = 25.05  # Sidereal rotation period at the equator

# Calculate rotation period in frames
# 1 day = BASE_FRAMES / EARTH_YEAR_DAYS frames
# T_frames = SUN_ROTATION_DAYS * (BASE_FRAMES / EARTH_YEAR_DAYS)
SUN_PERIOD_FRAMES = SUN_ROTATION_DAYS * (BASE_FRAMES / EARTH_YEAR_DAYS)

def setup_sun_rotation():
    print("\n🌞 Setting up accurate Sun rotation...")
    
    # Look for "The Sun" first, then fallback to "Sun", then to any object containing "sun"
    sun_obj = bpy.data.objects.get("The Sun")
    if not sun_obj:
        sun_obj = bpy.data.objects.get("Sun")
    if not sun_obj:
        for obj in bpy.data.objects:
            if "sun" in obj.name.lower():
                sun_obj = obj
                break
                
    if not sun_obj:
        print("  ✗ No object representing the Sun ('The Sun', 'Sun', etc.) found in the scene!")
        return False
        
    # Clear existing rotation animation / drivers to prevent conflicts
    if sun_obj.animation_data:
        # Remove rotation keyframes / drivers
        drivers = [d for d in sun_obj.animation_data.drivers if d.data_path == "rotation_euler"]
        for d in drivers:
            sun_obj.animation_data.drivers.remove(d)
            
        action = sun_obj.animation_data.action
        if action:
            fcurves = [fc for fc in action.fcurves if fc.data_path == "rotation_euler"]
            for fc in fcurves:
                action.fcurves.remove(fc)

    # 1. Set rotation mode to Euler XYZ
    sun_obj.rotation_mode = 'XYZ'
    
    # 2. Set axial tilt (rotate around X axis by 7.25 degrees)
    sun_obj.rotation_euler[0] = math.radians(SUN_TILT_DEG)
    sun_obj.rotation_euler[1] = 0.0
    
    # 3. Add driver to rotation_euler[2] (local Z rotation)
    fc = sun_obj.driver_add("rotation_euler", 2)
    drv = fc.driver
    drv.type = 'SCRIPTED'
    # Driver expression: (frame / period) * tau
    drv.expression = f"(frame / {SUN_PERIOD_FRAMES:.6f}) * {math.tau}"
    
    print(f"  ✓ Sun axial tilt set to {SUN_TILT_DEG}°")
    print(f"  ✓ Sun rotation period calibrated to {SUN_ROTATION_DAYS} days ({SUN_PERIOD_FRAMES:.4f} frames)")
    print(f"  ✓ Added rotation driver to local Z-axis: expression = '{drv.expression}'")
    print("  🌞 Sun rotation animation complete!\n")
    return True

if __name__ == "__main__":
    setup_sun_rotation()
