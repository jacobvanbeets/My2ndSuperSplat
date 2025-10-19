#!/usr/bin/env python3
"""
Standalone JSON Camera Generator
Creates camera animation JSON files without requiring Blender.
Compatible with SuperSplat camera format.

This script calculates camera positions mathematically and outputs
JSON directly, eliminating the need for Blender dependency.
"""

import json
import math
import argparse
import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Any

def focal_length_to_fov(focal_length: float, sensor_size: float = 32.0) -> float:
    """Convert focal length (mm) to horizontal field of view (degrees)
    
    Args:
        focal_length: Camera focal length in millimeters
        sensor_size: Sensor width in millimeters (default 32mm)
    
    Returns:
        Field of view in degrees
    """
    fov_radians = 2 * math.atan(sensor_size / (2 * focal_length))
    fov_degrees = math.degrees(fov_radians)
    return fov_degrees

def focal_length_to_fov(focal_length: float, sensor_size: float = 32.0) -> float:
    """Convert focal length (mm) to horizontal field of view (degrees)
    
    Args:
        focal_length: Camera focal length in millimeters
        sensor_size: Sensor width in millimeters (default 32mm)
    
    Returns:
        Field of view in degrees
    """
    fov_radians = 2 * math.atan(sensor_size / (2 * focal_length))
    fov_degrees = math.degrees(fov_radians)
    return fov_degrees

class StandaloneCameraGenerator:
    def __init__(self):
        self.poses = []
        self.metadata = {}
        
    def calculate_circular_path(self, 
                               center: Tuple[float, float, float],
                               radius: float,
                               frames: int,
                               direction: str = "clockwise") -> List[Tuple[float, float, float]]:
        """Calculate positions for circular camera path"""
        positions = []
        
        # Direction multiplier
        dir_mult = -1 if direction == "clockwise" else 1
        
        for frame in range(frames):
            # Calculate angle (full circle over all frames)
            angle = (2 * math.pi * frame / frames) * dir_mult
            
            # Calculate position
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            z = center[2]  # Height stays constant for circular
            
            positions.append((x, y, z))
            
        return positions
    
    def calculate_spiral_path(self,
                             center: Tuple[float, float, float],
                             start_radius: float,
                             end_radius: float,
                             start_height: float,
                             end_height: float,
                             loops: float,
                             frames: int,
                             direction: str = "clockwise") -> List[Tuple[float, float, float]]:
        """Calculate positions for spiral camera path"""
        positions = []
        
        # Direction multiplier
        dir_mult = -1 if direction == "clockwise" else 1
        
        for frame in range(frames):
            t = frame / (frames - 1) if frames > 1 else 0  # Normalized time [0, 1]
            
            # Calculate angle (multiple loops)
            angle = (2 * math.pi * loops * t) * dir_mult
            
            # Interpolate radius and height
            radius = start_radius + (end_radius - start_radius) * t
            height = start_height + (end_height - start_height) * t
            
            # Calculate position
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            z = center[2] + height
            
            positions.append((x, y, z))
            
        return positions
    
    def calculate_target_from_distance(self, 
                                     position: Tuple[float, float, float],
                                     center: Tuple[float, float, float],
                                     distance: float) -> Tuple[float, float, float]:
        """Calculate target position at specified distance from camera toward center"""
        px, py, pz = position
        cx, cy, cz = center
        
        # Vector from position to center
        dx = cx - px
        dy = cy - py  
        dz = cz - pz
        
        # Normalize the vector
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        if length == 0:
            return center  # Fallback if position equals center
            
        dx /= length
        dy /= length
        dz /= length
        
        # Calculate target at specified distance from camera
        tx = px + dx * distance
        ty = py + dy * distance
        tz = pz + dz * distance
        
        return (tx, ty, tz)
    
    def convert_coordinates(self, positions: List[Tuple[float, float, float]], 
                           targets: List[Tuple[float, float, float]]) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float, float]]]:
        """Convert from Blender Z-up to SuperSplat Y-up coordinate system"""
        converted_positions = []
        converted_targets = []
        
        # Blender to SuperSplat: X->X, Y->-Z, Z->Y
        for pos in positions:
            x, y, z = pos
            converted_positions.append((x, z, -y))
            
        for target in targets:
            x, y, z = target
            converted_targets.append((x, z, -y))
            
        return converted_positions, converted_targets
    
    def generate_camera_animation(self,
                                animation_type: str = "circular",
                                direction: str = "clockwise",
                                center: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                                target: Tuple[float, float, float] = None,
                                target_distance: float = None,
                                radius: float = 10.0,
                                start_radius: float = 5.0,
                                end_radius: float = 15.0,
                                start_height: float = 0.0,
                                end_height: float = 10.0,
                                spiral_loops: float = 2.0,
                                frames: int = 180,
                                fps: int = 24,
                                focal_length: float = 35.0,
                                sensor_size: float = 32.0,
                                convert_coords: bool = True,
                                precision: int = 6,
                                keyframe_step: int = 1) -> Dict[str, Any]:
        """Generate complete camera animation data"""
        
        # Calculate camera positions
        if animation_type == "circular":
            positions = self.calculate_circular_path(center, radius, frames, direction)
        elif animation_type == "spiral":
            positions = self.calculate_spiral_path(center, start_radius, end_radius, 
                                                 start_height, end_height, spiral_loops, 
                                                 frames, direction)
        else:
            raise ValueError(f"Unknown animation type: {animation_type}")
        
        # Calculate targets
        targets = []
        if target_distance is not None:
            # Auto-calculate targets based on distance
            for pos in positions:
                tgt = self.calculate_target_from_distance(pos, center, target_distance)
                targets.append(tgt)
        elif target is not None:
            # Use fixed target for all frames
            targets = [target] * frames
        else:
            # Default to center as target
            targets = [center] * frames
        
        # Convert coordinate system if requested
        if convert_coords:
            positions, targets = self.convert_coordinates(positions, targets)
        
        # Round to specified precision
        def round_tuple(t, precision):
            return tuple(round(x, precision) for x in t)
            
        positions = [round_tuple(pos, precision) for pos in positions]
        targets = [round_tuple(tgt, precision) for tgt in targets]
        
        # Calculate field of view from focal length
        fov = focal_length_to_fov(focal_length, sensor_size)
        
        # Create poses with SuperSplat-compatible format and keyframe filtering
        poses = []
        for i, (pos, tgt) in enumerate(zip(positions, targets)):
            # Only create keyframes at specified intervals (plus first and last frame)
            if i % keyframe_step == 0 or i == len(positions) - 1:
                frame_num = i + 1  # SuperSplat expects 1-based frame numbers
                pose = {
                    "frame": frame_num,
                    "time": frame_num / fps,
                    "position": list(pos),
                    "target": list(tgt),
                    "focal_length": focal_length,
                    "fov": round(fov, 2),  # Field of view in degrees
                    "name": f"camera_frame_{frame_num:04d}"
                }
                poses.append(pose)
        
        # Create SuperSplat-compatible JSON structure
        json_data = {
            "camera_name": "Generated_Camera",
            "frame_rate": fps,
            "frame_start": 1,
            "frame_end": frames,
            "frame_step": 1,
            "coordinate_system": "SUPERSPLAT" if convert_coords else "BLENDER",
            "total_frames": frames,
            "keyframes_generated": len(poses),
            "keyframe_step": keyframe_step,
            "animation_type": animation_type,
            "direction": direction,
            "export_timestamp": datetime.now().isoformat(),
            "coordinate_precision": precision,
            "center": list(center),
            "poses": poses
        }
        
        # Add target information
        if target_distance is not None:
            json_data["target_distance"] = target_distance
        else:
            if target:
                json_data["target"] = list(target)
        
        # Add type-specific parameters
        if animation_type == "circular":
            json_data["radius"] = radius
        elif animation_type == "spiral":
            json_data.update({
                "spiral_loops": spiral_loops,
                "start_radius": start_radius,
                "end_radius": end_radius,
                "start_height": start_height,
                "end_height": end_height,
            })
        
        # Add generator info as metadata
        json_data["generator"] = "Standalone Camera JSON Generator v1.0"
        
        return json_data
    
    def save_json(self, data: Dict[str, Any], output_path: str) -> None:
        """Save camera animation data to JSON file"""
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def parse_coordinates(coord_str: str) -> Tuple[float, float, float]:
    """Parse coordinate string like '0,0,0' into tuple"""
    try:
        parts = [float(x.strip()) for x in coord_str.split(',')]
        if len(parts) != 3:
            raise ValueError("Coordinates must have exactly 3 values")
        return tuple(parts)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid coordinates '{coord_str}': {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate camera animation JSON files (without Blender)')
    
    # Animation type
    parser.add_argument('--animation-type', choices=['circular', 'spiral'], 
                       default='circular', help='Type of animation')
    parser.add_argument('--direction', choices=['clockwise', 'counterclockwise'], 
                       default='clockwise', help='Animation direction')
    
    # Positioning
    parser.add_argument('--center', type=parse_coordinates, default='0,0,0',
                       help='Center coordinates (x,y,z)')
    parser.add_argument('--target', type=parse_coordinates, default=None,
                       help='Fixed target coordinates (x,y,z)')
    parser.add_argument('--target-distance', type=float, default=None,
                       help='Auto-calculate target at this distance from camera')
    
    # Circular parameters
    parser.add_argument('--radius', type=float, default=10.0,
                       help='Radius for circular animation')
    
    # Spiral parameters
    parser.add_argument('--start-radius', type=float, default=5.0,
                       help='Starting radius for spiral animation')
    parser.add_argument('--end-radius', type=float, default=15.0,
                       help='Ending radius for spiral animation')
    parser.add_argument('--start-height', type=float, default=0.0,
                       help='Starting height for spiral animation')
    parser.add_argument('--end-height', type=float, default=10.0,
                       help='Ending height for spiral animation')
    parser.add_argument('--spiral-loops', type=float, default=2.0,
                       help='Number of loops for spiral animation')
    
    # Animation settings
    parser.add_argument('--frames', type=int, default=180,
                       help='Number of animation frames')
    parser.add_argument('--fps', type=int, default=24,
                       help='Frames per second')
    parser.add_argument('--focal-length', type=float, default=35.0,
                       help='Camera focal length in mm')
    parser.add_argument('--sensor-size', type=float, default=32.0,
                       help='Camera sensor width in mm (32=standard, 36=full-frame)')
    
    # Export options
    parser.add_argument('--convert-coords', action='store_true', default=False,
                       help='Convert from Blender Z-up to SuperSplat Y-up coordinates')
    parser.add_argument('--precision', type=int, default=6, choices=range(1, 15),
                       help='Decimal precision for coordinates')
    parser.add_argument('--keyframe-step', type=int, default=1, 
                       help='Generate keyframes every N frames (1 = every frame, 2 = every other frame, etc.)')
    
    # Output
    parser.add_argument('--output', type=str, required=True,
                       help='Output JSON file path')
    
    args = parser.parse_args()
    
    try:
        generator = StandaloneCameraGenerator()
        
        # Handle target specification
        target = args.target
        target_distance = args.target_distance
        
        # If neither target nor target_distance specified, use default target
        if target is None and target_distance is None:
            target = (0.0, 0.0, -10.0)  # Default target
        
        # Generate animation data
        data = generator.generate_camera_animation(
            animation_type=args.animation_type,
            direction=args.direction,
            center=args.center,
            target=target,
            target_distance=target_distance,
            radius=args.radius,
            start_radius=args.start_radius,
            end_radius=args.end_radius,
            start_height=args.start_height,
            end_height=args.end_height,
            spiral_loops=args.spiral_loops,
            frames=args.frames,
            fps=args.fps,
            focal_length=args.focal_length,
            sensor_size=args.sensor_size,
            convert_coords=args.convert_coords,
            precision=args.precision,
            keyframe_step=args.keyframe_step
        )
        
        # Save to file
        generator.save_json(data, args.output)
        
        # Print success message
        print(f"✓ SUCCESS! JSON camera animation generated.")
        print(f"✓ File: {args.output}")
        print(f"✓ Type: {args.animation_type.title()} ({args.direction})")
        print(f"✓ Frames: {args.frames} ({args.frames/args.fps:.1f} seconds at {args.fps} FPS)")
        print(f"✓ Keyframes: {len(data['poses'])} (every {args.keyframe_step} frame{'s' if args.keyframe_step > 1 else ''})")
        print(f"✓ Coordinate System: {'Y-up (SuperSplat)' if args.convert_coords else 'Z-up (Blender)'}")
        print("")
        print("Ready for SuperSplat:")
        print("1. Open SuperSplat")
        print("2. Import your JSON camera file")
        print("3. Load the animation in the Camera Poses panel")
        
    except Exception as e:
        print(f"✗ ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
