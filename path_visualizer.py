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
        
        print(f"✓ Loaded floorplan: {self.width:.1f} x {self.height:.1f}")
        print(f"✓ Obstacles: {len(self.obstacles)}")
    
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
    
    def _create_svg(self, 
                    viewpoint: Tuple[float, float],
                    path_coords: List[Tuple[float, float]],
                    current_point_idx: int,
                    visibility_polygon: List[Tuple[float, float]],
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
        
        # Draw visibility polygon (isovist)
        if visibility_polygon:
            dwg.add(dwg.polygon(
                points=visibility_polygon,
                fill='rgb(200, 200, 200)',
                fill_opacity=0.4,
                stroke='rgb(150, 150, 150)',
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
                         format: str = "svg") -> List[str]:
        """
        Generate visualization sequence for a path
        
        Args:
            path_id: Specific path ID to visualize (None = all paths)
            output_dir: Directory to save output files
            format: Output format ('svg', 'png', or 'both')
            
        Returns:
            List of generated file paths
        """
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        # Get paths to process
        features = self.paths_data.get('features', [])
        if path_id:
            features = [f for f in features if f['properties']['id'] == path_id]
            if not features:
                print(f"Error: Path '{path_id}' not found")
                return []
        
        # Process each path
        for feature in features:
            props = feature['properties']
            current_path_id = props['id']
            coords = feature['geometry']['coordinates']
            
            print(f"\nProcessing path '{current_path_id}' with {len(coords)} points...")
            
            # Generate image for each point
            for idx, (x, y) in enumerate(coords):
                viewpoint = (x, y)
                
                print(f"  Point {idx + 1}/{len(coords)}: ({x:.1f}, {y:.1f})...", end=" ")
                
                # Compute visibility polygon
                visibility = self._compute_visibility(viewpoint)
                
                # Create SVG
                dwg = self._create_svg(
                    viewpoint=viewpoint,
                    path_coords=coords,
                    current_point_idx=idx,
                    visibility_polygon=visibility,
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
    parser.add_argument('--path-id', help='Specific path ID to visualize (default: all paths)')
    parser.add_argument('--output-dir', default='./output', help='Output directory (default: ./output)')
    parser.add_argument('--format', choices=['svg', 'png', 'both'], default='svg',
                       help='Output format (default: svg)')
    
    args = parser.parse_args()
    
    # Validate input files
    if not os.path.exists(args.floorplan):
        print(f"Error: Floorplan file not found: {args.floorplan}")
        sys.exit(1)
    
    if not os.path.exists(args.paths):
        print(f"Error: Paths file not found: {args.paths}")
        sys.exit(1)
    
    # Create visualizer
    visualizer = IsovistPathVisualizer(args.floorplan, args.paths)
    
    # Generate sequence
    files = visualizer.generate_sequence(
        path_id=args.path_id,
        output_dir=args.output_dir,
        format=args.format
    )
    
    print(f"\n{'='*60}")
    print(f"Generated {len(files)} files in '{args.output_dir}'")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()