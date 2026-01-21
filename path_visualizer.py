#!/usr/bin/env python3
"""
Isovist Path Visualizer - CLI Application

Generates a sequence of SVG/PNG images showing visibility polygons (isovists)
along a pedestrian path through a floorplan.

Usage:
    python isovist_path_visualizer.py <floorplan.geojson> <paths.json> [options]

Example:
    python isovist_path_visualizer.py floorplan.geojson paths.json --output-dir ./output --format both
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import argparse

try:
    import svgwrite
except ImportError:
    print("Error: svgwrite not installed. Install with: pip install svgwrite")
    sys.exit(1)

# Try to load visibility module - support both loading methods
_visibility_module = None
try:
    from visibility_module import get_visibility_module
    _visibility_module = get_visibility_module()
    print("✓ Loaded visibility module via visibility_module.py")
except ImportError:
    import platform
    print("\n" + "="*60)
    print("ERROR: Visibility module not found")
    print("="*60)
    print(f"\nCurrent OS: {platform.system()}")
    print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}")
    print(f"\nYou need:")
    print("  1. visibility_module.py OR visibility_loader.py")
    print("  2. Compiled C++ extension for your OS:")
    if platform.system() == "Darwin":
        print(f"     - visibility_polygon.cpython-{sys.version_info.major}{sys.version_info.minor}-darwin.so")
    elif platform.system() == "Windows":
        print(f"     - visibility_polygon.cp{sys.version_info.major}{sys.version_info.minor}-win_amd64.pyd")
    elif platform.system() == "Linux":
        print(f"     - visibility_polygon.cpython-{sys.version_info.major}{sys.version_info.minor}-x86_64-linux-gnu.so")
    print("\nFiles should be in the same directory as this script or in PYTHONPATH")
    print("="*60)
    sys.exit(1)


class IsovistPathVisualizer:
    """Generate isovist visualizations along a path"""
    
    def __init__(self, floorplan_path: str, paths_path: str):
        """
        Initialize visualizer with floorplan and path data
        
        Args:
            floorplan_path: Path to floorplan GeoJSON file
            paths_path: Path to trajectory paths JSON file
        """
        global _visibility_module
        
        self.floorplan_data = self._load_json(floorplan_path)
        self.paths_data = self._load_json(paths_path)
        self.vis_module = _visibility_module
        
        if self.vis_module is None:
            raise RuntimeError("Visibility module not loaded. Check installation.")
        
        # Extract floorplan metadata
        metadata = self.floorplan_data.get('metadata', {})
        self.viewbox = metadata.get('viewBox', {})
        self.width = self.viewbox.get('width', 800)
        self.height = self.viewbox.get('height', 600)
        
        # Extract obstacles from floorplan
        self.obstacles = self._extract_obstacles()

        print("\nDiagnostic - Polygon winding order:")
        for i, obs in enumerate(self.obstacles):
            obs_cartesian = [(x, self.height - y) for x, y in obs]
            winding = self._check_polygon_winding(obs_cartesian)
            print(f"  Obstacle {i}: {winding} ({len(obs)} points)")

        # Merge obstacles too close to boundaries
        self.obstacles = self._merge_boundary_adjacent_obstacles(tolerance=2.0)

        print(f"✓ Loaded floorplan: {self.width:.1f} x {self.height:.1f}")
        print(f"✓ Obstacles: {len(self.obstacles)}")

        self.boundary_diagonal = self._calculate_boundary_diagonal()
        print(f"✓ Boundary diagonal: {self.boundary_diagonal:.1f}px")

        # Initialize allocentric mode parameters (will be set by generate_sequence)
        self.allocentric_mode = False
        self.visibility_data = None
        self.target_obstacle = None
    
    def _check_polygon_winding(self, points: List[Tuple[float, float]]) -> str:
        """
        Check if polygon has clockwise or counter-clockwise winding
        Returns: 'cw' for clockwise, 'ccw' for counter-clockwise
        """
        # Calculate signed area
        area = 0.0
        for i in range(len(points)):
            j = (i + 1) % len(points)
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return 'ccw' if area > 0 else 'cw'

    def _load_json(self, filepath: str) -> dict:
        """Load and parse JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _extract_obstacles(self) -> List[List[Tuple[float, float]]]:
        """Extract obstacle polygons from floorplan GeoJSON"""
        obstacles = []
        for feature in self.floorplan_data.get('features', []):
            if feature.get('properties', {}).get('type') in ['boundary', 'obstacle']:
                coords = feature['geometry']['coordinates'][0]
                # Convert Cartesian (bottom-left origin) to SVG (top-left origin)
                svg_coords = [(x, self.height - y) for x, y in coords]
                obstacles.append(svg_coords)
        return obstacles
    
    def _compute_visibility(self, viewpoint: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Compute visibility polygon from a viewpoint
        
        Args:
            viewpoint: (x, y) in Cartesian coordinates
            
        Returns:
            List of (x, y) points defining visibility polygon in SVG coordinates
        """
        try:
            # Convert viewpoint from Cartesian to format expected by module
            vp_cartesian = (viewpoint[0], viewpoint[1])
            
            # Create Point object
            pov = self.vis_module.module.Point(float(vp_cartesian[0]), float(vp_cartesian[1]))
            
            # Create obstacle polygons
            obstacle_list = []
            for obstacle_points in self.obstacles:
                poly = self.vis_module.module.Polygon2()
                # Convert back from SVG to Cartesian for C++ module
                for x, svg_y in obstacle_points:
                    cartesian_y = self.height - svg_y
                    poly.add_vertex(float(x), float(cartesian_y))
                obstacle_list.append(poly)
            
            # Compute visibility polygon
            visibility_points = self.vis_module.module.compute_visibility_polygon(
                pov,
                obstacle_list,
                int(self.width),
                int(self.height),
                3000.0  # ray_length
            )
            
            # Convert result from Cartesian to SVG coordinates
            return [(p.x, self.height - p.y) for p in visibility_points]
            
        except Exception as e:
            print(f"\n✗ Error computing visibility from ({viewpoint[0]:.1f}, {viewpoint[1]:.1f})")
            print(f"  {str(e)}")
            raise RuntimeError(f"Visibility computation failed: {e}")
    
    def _compute_allocentric_visibility(
        self,
        obstacle_index: int,
        visibility_value: float
    ) -> List[Tuple[float, float]]:
        """
        Compute allocentric visibility from obstacle center with radius clipping
        
        Args:
            obstacle_index: Index of the obstacle (1-based matching JSON keys)
            visibility_value: Normalized visibility value (0-1)
            
        Returns:
            List of (x, y) points defining clipped visibility polygon in SVG coordinates
        """
        try:
            # Get the obstacle polygon (stored in SVG coordinates)
            obstacle_svg = self.obstacles[obstacle_index]
            
            # Convert from SVG to Cartesian coordinates
            obstacle_cartesian = [(x, self.height - y) for x, y in obstacle_svg]
            
            # Calculate obstacle center (in Cartesian coordinates)
            # Exclude duplicate closing point if present
            points_to_average = obstacle_cartesian
            if len(obstacle_cartesian) > 1:
                first = obstacle_cartesian[0]
                last = obstacle_cartesian[-1]
                if abs(first[0] - last[0]) < 0.01 and abs(first[1] - last[1]) < 0.01:
                    points_to_average = obstacle_cartesian[:-1]
            
            center_x = sum(x for x, y in points_to_average) / len(points_to_average)
            center_y = sum(y for x, y in points_to_average) / len(points_to_average)
            
            print(f"  Allocentric center (Cartesian): ({center_x:.1f}, {center_y:.1f})")
            
            # Create Point for the center
            pov = self.vis_module.module.Point(float(center_x), float(center_y))
            
            # Create obstacle polygons EXCLUDING the target obstacle
            # Need to convert from SVG to Cartesian for C++ module
            obstacle_list = []
            for i, obstacle_points in enumerate(self.obstacles):
                if i == obstacle_index:
                    print(f"  Excluding obstacle {i} from allocentric computation")
                    continue  # Skip the target obstacle
                    
                poly = self.vis_module.module.Polygon2()
                # Convert back from SVG to Cartesian for C++ module
                for x, svg_y in obstacle_points:
                    cartesian_y = self.height - svg_y
                    poly.add_vertex(float(x), float(cartesian_y))
                obstacle_list.append(poly)
            
            print(f"  Computing with {len(obstacle_list)} obstacles (excluded obstacle {obstacle_index})")
            
            # Compute visibility polygon (returns Point objects)
            visibility_points = self.vis_module.module.compute_visibility_polygon(
                pov,
                obstacle_list,
                int(self.width),
                int(self.height),
                3000.0  # ray_length
            )
            
            print(f"  Unclipped allocentric polygon: {len(visibility_points)} points")
            
            # Calculate radius: 0 = 0, 1 = boundary diagonal
            radius = visibility_value * self.boundary_diagonal
            
            print(f"  Visibility value: {visibility_value:.2f}")
            print(f"  Boundary diagonal: {self.boundary_diagonal:.1f}px")
            print(f"  Clipping radius: {radius:.1f}px")
            
            # Clip with circle using Clipper2
            # Pass Point objects (not tuples!)
            clipped_points = self.vis_module.module.clip_circle_with_visibility_polygon(
                visibility_points,  # Point objects from compute_visibility_polygon
                pov,                # Point object for center
                float(radius),
                128  # circle segments for smooth clipping
            )
            
            print(f"  Clipped allocentric polygon: {len(clipped_points)} points")
            
            if len(clipped_points) == 0:
                print(f"  ✗ WARNING: Clipping returned empty polygon!")
                return []
            
            # Convert from Cartesian to SVG coordinates
            result = [(p.x, self.height - p.y) for p in clipped_points]
            
            print(f"  ✓ Allocentric visibility computed successfully")
            
            return result
            
        except Exception as e:
            print(f"\n✗ Error computing allocentric visibility:")
            print(f"  {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _merge_boundary_adjacent_obstacles(self, tolerance: float = 2.0) -> List[List[Tuple[float, float]]]:
        """
        Merge obstacles that are within tolerance distance of the boundary
        
        Args:
            tolerance: Maximum distance (in pixels) to consider "adjacent to boundary"
        
        Returns:
            Modified list of obstacles with boundary-adjacent ones merged
        """
        if len(self.obstacles) < 2:
            return self.obstacles
        
        boundary = self.obstacles[0]
        boundary_cartesian = [(x, self.height - y) for x, y in boundary]
        
        # Get boundary extents
        min_x = min(x for x, y in boundary_cartesian)
        max_x = max(x for x, y in boundary_cartesian)
        min_y = min(y for x, y in boundary_cartesian)
        max_y = max(y for x, y in boundary_cartesian)
        
        modified_obstacles = [boundary]  # Keep original boundary
        
        for i, obstacle in enumerate(self.obstacles[1:], start=1):
            obstacle_cartesian = [(x, self.height - y) for x, y in obstacle]
            
            # Check if any vertex is too close to boundary edges
            too_close = False
            for x, y in obstacle_cartesian:
                if (abs(x - min_x) < tolerance or abs(x - max_x) < tolerance or
                    abs(y - min_y) < tolerance or abs(y - max_y) < tolerance):
                    too_close = True
                    print(f"  WARNING: Obstacle {i} is within {tolerance}px of boundary - adjusting")
                    break
            
            if too_close:
                # Adjust obstacle vertices to be exactly on boundary or further away
                adjusted = []
                for x, y in obstacle_cartesian:
                    new_x = x
                    new_y = y
                    
                    # Snap to boundary if within tolerance
                    if abs(x - min_x) < tolerance:
                        new_x = min_x
                    if abs(x - max_x) < tolerance:
                        new_x = max_x
                    if abs(y - min_y) < tolerance:
                        new_y = min_y
                    if abs(y - max_y) < tolerance:
                        new_y = max_y
                    
                    adjusted.append((new_x, new_y))
                
                # Convert back to SVG
                adjusted_svg = [(x, self.height - y) for x, y in adjusted]
                modified_obstacles.append(adjusted_svg)
            else:
                modified_obstacles.append(obstacle)
        
        return modified_obstacles

    def _calculate_boundary_diagonal(self) -> float:
        """Calculate the diagonal of the boundary polygon (first obstacle)"""
        if not self.obstacles or len(self.obstacles) < 1:
            return 1000.0  # Default fallback
        
        boundary = self.obstacles[0]
        
        # Find min/max coordinates
        min_x = min(x for x, y in boundary)
        max_x = max(x for x, y in boundary)
        min_y = min(y for x, y in boundary)
        max_y = max(y for x, y in boundary)
        
        # Calculate diagonal
        width = max_x - min_x
        height = max_y - min_y
        diagonal = (width**2 + height**2)**0.5
        
        return diagonal

    def _create_svg(self, 
                viewpoint: Tuple[float, float],
                path_coords: List[Tuple[float, float]],
                current_point_idx: int,
                visibility_polygon: List[Tuple[float, float]],
                allocentric_polygon: Optional[List[Tuple[float, float]]],
                path_id: str) -> svgwrite.Drawing:
        """
        Create SVG drawing with floorplan, path, and isovist
        
        Args:
            viewpoint: Current viewpoint in Cartesian coordinates
            path_coords: All path coordinates in Cartesian
            current_point_idx: Index of current point in path
            visibility_polygon: Visibility polygon in SVG coordinates
            path_id: Identifier for the path
            
        Returns:
            svgwrite.Drawing object
        """
        # Convert Cartesian viewpoint to SVG
        vp_svg = (viewpoint[0], self.height - viewpoint[1])
        
        # Create SVG with padding for labels
        dwg = svgwrite.Drawing(
            size=(f"{self.width}px", f"{self.height}px"),
            viewBox=f"0 0 {self.width} {self.height}"
        )
        
        # Add background
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=(self.width, self.height),
            fill='white'
        ))
        
        # Draw floorplan boundary and obstacles
        for i, obstacle in enumerate(self.obstacles):
            points = [(x, y) for x, y in obstacle]
            
            if i == 0:  # Boundary
                dwg.add(dwg.polygon(
                    points=points,
                    fill='none',
                    stroke='#666666',
                    stroke_width=2,
                    stroke_dasharray='5,5'
                ))
            else:  # Obstacles
                dwg.add(dwg.polygon(
                    points=points,
                    fill='#e0e0e0',
                    stroke='#333333',
                    stroke_width=2
                ))
        
        # Draw allocentric visibility polygon FIRST (if in allocentric mode)
        # This is the clipped isovist from the obstacle center
        if allocentric_polygon and len(allocentric_polygon) > 0:
            dwg.add(dwg.polygon(
                points=allocentric_polygon,
                fill='rgb(150, 150, 150)',  # Medium gray fill
                fill_opacity=0.5,
                stroke='rgb(100, 100, 100)',  # Darker gray stroke
                stroke_opacity=0.8,
                stroke_width=2
            ))
            
            # Draw obstacle center indicator
            obstacle_svg = self.obstacles[self.target_obstacle]
            # Convert to Cartesian for center calculation
            obstacle_cartesian = [(x, self.height - y) for x, y in obstacle_svg]
            points_to_average = obstacle_cartesian
            if len(obstacle_cartesian) > 1:
                first = obstacle_cartesian[0]
                last = obstacle_cartesian[-1]
                if abs(first[0] - last[0]) < 0.01 and abs(first[1] - last[1]) < 0.01:
                    points_to_average = obstacle_cartesian[:-1]
            
            center_x = sum(x for x, y in points_to_average) / len(points_to_average)
            center_y = sum(y for x, y in points_to_average) / len(points_to_average)
            # Convert center back to SVG for drawing
            center_svg_x = center_x
            center_svg_y = self.height - center_y
            
            # Draw obstacle center marker
            dwg.add(dwg.circle(
                center=(center_svg_x, center_svg_y),
                r=6,
                fill='#000000',
                stroke='white',
                stroke_width=2
            ))

        # Draw visibility polygon (isovist from path POV)
        # This is the unclipped isovist from the current viewpoint
        if visibility_polygon:
            dwg.add(dwg.polygon(
                points=visibility_polygon,
                fill='rgb(200, 200, 200)',  # Light gray fill
                fill_opacity=0.4,
                stroke='rgb(150, 150, 150)',  # Medium gray stroke
                stroke_opacity=0.8,
                stroke_width=2
            ))
        
        # Draw complete path
        path_svg_coords = [(x, self.height - y) for x, y in path_coords]
        
        # Draw path lines
        for i in range(len(path_svg_coords) - 1):
            dwg.add(dwg.line(
                start=path_svg_coords[i],
                end=path_svg_coords[i + 1],
                stroke='#888888',
                stroke_width=3,
                opacity=0.6
            ))
        
        # Draw path points
        for i, (x, y) in enumerate(path_svg_coords):
            if i == current_point_idx:
                # Current viewpoint - larger, highlighted
                dwg.add(dwg.circle(
                    center=(x, y),
                    r=8,
                    fill='#000000',
                    stroke='white',
                    stroke_width=3
                ))
            elif i < current_point_idx:
                # Past points
                dwg.add(dwg.circle(
                    center=(x, y),
                    r=5,
                    fill='#999999',
                    stroke='white',
                    stroke_width=2
                ))
            else:
                # Future points
                dwg.add(dwg.circle(
                    center=(x, y),
                    r=5,
                    fill='#E0E0E0',
                    stroke='white',
                    stroke_width=2
                ))
        
        # Add labels
        # title_text = f"Path: {path_id} | Point {current_point_idx + 1}/{len(path_coords)}"
        # dwg.add(dwg.text(
        #     title_text,
        #     insert=(10, 20),
        #     fill='#333333',
        #     font_size='16px',
        #     font_family='Arial, sans-serif',
        #     font_weight='bold'
        # ))
        
        # coord_text = f"Position: ({viewpoint[0]:.1f}, {viewpoint[1]:.1f})"
        # dwg.add(dwg.text(
        #     coord_text,
        #     insert=(10, 40),
        #     fill='#666666',
        #     font_size='14px',
        #     font_family='Arial, sans-serif'
        # ))
        
        return dwg
    
    def generate_sequence(self, 
                     path_id: Optional[str] = None,
                     output_dir: str = "./output",
                     format: str = "svg",
                     allocentric_mode: bool = False,
                     visibility_data: Optional[Dict] = None,
                     target_obstacle: Optional[int] = None) -> List[str]:
        """
        Generate visualization sequence for a path
        
        Args:
            path_id: Specific path ID to visualize (None = all paths)
            output_dir: Directory to save output files
            format: Output format ('svg', 'png', or 'both')
            
        Returns:
            List of generated file paths
        """

        # Update allocentric mode parameters
        self.allocentric_mode = allocentric_mode
        self.visibility_data = visibility_data
        self.target_obstacle = target_obstacle

        if self.allocentric_mode:
            obstacle_key = f"obstacle{target_obstacle}"
            vis_value = visibility_data[obstacle_key]['visibility']
            print(f"✓ Allocentric mode: Obstacle {target_obstacle}, Visibility: {vis_value:.2f}")

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        features = self.paths_data.get('features', [])
        if path_id:
            features = [f for f in features if f['properties']['id'] == path_id]
            if not features:
                print(f"Error: Path '{path_id}' not found")
                return []
        
        for feature in features:
            props = feature['properties']
            current_path_id = props['id']
            coords = feature['geometry']['coordinates']
            
            print(f"\nProcessing path '{current_path_id}' with {len(coords)} points...")
            
            # Generate image for each point
            for idx, (x, y) in enumerate(coords):
                viewpoint = (x, y)
                
                print(f"  Point {idx + 1}/{len(coords)}: ({x:.1f}, {y:.1f})...", end=" ")
                
                # Compute visibility polygon from path POV
                visibility = self._compute_visibility(viewpoint)
                
                # Compute allocentric visibility if in allocentric mode
                allocentric_visibility = None
                if self.allocentric_mode and self.target_obstacle is not None:
                    obstacle_key = f"obstacle{self.target_obstacle}"
                    vis_value = self.visibility_data[obstacle_key]['visibility']
                    allocentric_visibility = self._compute_allocentric_visibility(
                        self.target_obstacle,
                        vis_value
                    )
                
                dwg = self._create_svg(
                    viewpoint=viewpoint,
                    path_coords=coords,
                    current_point_idx=idx,
                    visibility_polygon=visibility,
                    allocentric_polygon=allocentric_visibility,
                    path_id=current_path_id
                )
                
                # Save files
                base_filename = f"{current_path_id}_point_{idx:03d}"
                
                if format in ['svg', 'both']:
                    svg_path = os.path.join(output_dir, f"{base_filename}.svg")
                    dwg.save()
                    dwg.saveas(svg_path)
                    generated_files.append(svg_path)
                    print(f"✓ SVG", end="")
                
                if format in ['png', 'both']:
                    # Convert to PNG using cairosvg
                    try:
                        import cairosvg
                        svg_path = os.path.join(output_dir, f"{base_filename}.svg")
                        png_path = os.path.join(output_dir, f"{base_filename}.png")
                        
                        if format == 'both':
                            # SVG already saved, just convert
                            cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=150)
                        else:
                            # Save SVG temporarily then convert
                            dwg.saveas(svg_path)
                            cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=150)
                            os.remove(svg_path)  # Remove temporary SVG
                        
                        generated_files.append(png_path)
                        print(f" + PNG", end="")
                    except ImportError:
                        print("\nWarning: cairosvg not installed. Install with: pip install cairosvg")
                        print("Falling back to SVG only")
                        if format == 'png':
                            svg_path = os.path.join(output_dir, f"{base_filename}.svg")
                            dwg.saveas(svg_path)
                            generated_files.append(svg_path)
                
                print()  # New line
            
            print(f"✓ Completed path '{current_path_id}'")
        
        return generated_files


def main():
    parser = argparse.ArgumentParser(
        description='Generate isovist visualizations along pedestrian paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate SVG sequence for all paths
  python isovist_path_visualizer.py floorplan.geojson paths.json
  
  # Generate PNG sequence for specific path
  python isovist_path_visualizer.py floorplan.geojson paths.json --path-id path1 --format png
  
  # Generate both SVG and PNG
  python isovist_path_visualizer.py floorplan.geojson paths.json --format both --output-dir ./renders
        """
    )
    
    parser.add_argument('floorplan', help='Floorplan GeoJSON file')
    parser.add_argument('paths', help='Paths JSON file')
    parser.add_argument('-a', '--allocentric', metavar='VISIBILITY_VALUES',
                    help='Enable allocentric mode with visibility values JSON file')
    parser.add_argument('-o', '--obstacle', type=int, dest='obstacle_index',
                    help='Obstacle index (required in allocentric mode)')
    parser.add_argument('--path-id', help='Specific path ID to visualize (default: all paths)')
    parser.add_argument('--output-dir', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--format', choices=['svg', 'png', 'both'], default='svg',
                    help='Output format (default: svg)')
    
    args = parser.parse_args()
    
    if args.allocentric:
        if args.obstacle_index is None:
            parser.error("Obstacle index is required when using allocentric mode (-a)")
        if not os.path.exists(args.allocentric):
            parser.error(f"Visibility values file not found: {args.allocentric}")
    elif args.obstacle_index is not None:
        parser.error("Obstacle index can only be specified in allocentric mode (use -a flag)")

    # Validate input files
    if not os.path.exists(args.floorplan):
        print(f"Error: Floorplan file not found: {args.floorplan}")
        sys.exit(1)
    
    if not os.path.exists(args.paths):
        print(f"Error: Paths file not found: {args.paths}")
        sys.exit(1)
    
    # Load visibility values if in allocentric mode
    visibility_data = None
    target_obstacle = None
    if args.allocentric:
        with open(args.allocentric, 'r') as f:
            visibility_values = json.load(f)
        
        # Map obstacle index to JSON key
        obstacle_key = f"obstacle{args.obstacle_index}"
        
        if obstacle_key not in visibility_values:
            print(f"Error: {obstacle_key} not found in visibility values file")
            print(f"Available obstacles: {', '.join(visibility_values.keys())}")
            sys.exit(1)
        
        visibility_data = visibility_values
        target_obstacle = args.obstacle_index
        print(f"Allocentric mode enabled: Target obstacle {args.obstacle_index} (visibility: {visibility_values[obstacle_key]['visibility']})")

    # Create visualizer
    visualizer = IsovistPathVisualizer(args.floorplan, args.paths)

    # Generate sequence
    files = visualizer.generate_sequence(
        path_id=args.path_id,
        output_dir=args.output_dir,
        format=args.format,
        allocentric_mode=args.allocentric is not None,
        visibility_data=visibility_data,
        target_obstacle=target_obstacle
    )
    
    print(f"\n{'='*60}")
    print(f"Generated {len(files)} files in '{args.output_dir}'")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()