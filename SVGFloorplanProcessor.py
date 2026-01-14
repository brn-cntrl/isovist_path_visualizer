import xml.etree.ElementTree as ET
import json
import re
from typing import List, Dict, Tuple, Optional
import os

class SVGFloorplanProcessor:
    """
    Process SVG floorplans for visibility polygon calculations.
    Handles doubled geometry from stroke widths and converts to GeoJSON.
    Uses only standard library - no external dependencies.
    """
    
    def __init__(self):
        self.tree = None
        self.root = None
        self.ns = {'svg': 'http://www.w3.org/2000/svg'}
        self.geometries = []
        self.geojson_data = None
        self.viewbox = None
        self.parent_map = {}
        
    def import_svg(self, filepath: str) -> 'SVGFloorplanProcessor':
        """
        Import an SVG file.
        
        Args:
            filepath: Path to the SVG file
            
        Returns:
            self for method chaining
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"SVG file not found: {filepath}")
        
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()
        
        # Build parent map for finding parent groups
        self.parent_map = {c: p for p in self.root.iter() for c in p}
        
        # Extract viewBox dimensions
        viewbox = self.root.get('viewBox')
        if viewbox:
            parts = viewbox.split()
            self.viewbox = {
                'x': float(parts[0]),
                'y': float(parts[1]),
                'width': float(parts[2]),
                'height': float(parts[3])
            }
        else:
            # Fallback to width/height attributes
            width = self.root.get('width', '0')
            height = self.root.get('height', '0')
            # Remove units if present
            width = re.sub(r'[^\d.]', '', width)
            height = re.sub(r'[^\d.]', '', height)
            
            self.viewbox = {
                'x': 0,
                'y': 0,
                'width': float(width) if width else 0,
                'height': float(height) if height else 0
            }
        
        print(f"✓ Imported SVG: {filepath}")
        print(f"  ViewBox: {self.viewbox['width']} x {self.viewbox['height']}")
        
        return self
    
    def clean_svg(self, keep_groups: bool = True) -> 'SVGFloorplanProcessor':
        """
        Clean SVG by extracting only outer path boundaries.
        Removes doubled geometry caused by stroke widths.
        
        Args:
            keep_groups: Whether to preserve group structure
            
        Returns:
            self for method chaining
        """
        if self.tree is None:
            raise ValueError("No SVG loaded. Call import_svg() first.")
        
        paths = self.root.findall('.//svg:path', self.ns)
        self.geometries = []
        cleaned_count = 0
        
        for path_elem in paths:
            d = path_elem.get('d')
            if not d:
                continue
            
            # Split by 'M' to identify subpaths (doubled geometry)
            # The pattern matches 'M' followed by coordinates
            subpaths = re.split(r'(?=[Mm])', d)
            subpaths = [sp.strip() for sp in subpaths if sp.strip()]
            
            if not subpaths:
                continue
            
            # Extract only the first (outer) subpath
            outer_path = subpaths[0]
            
            # Parse and extract coordinates
            try:
                points = self._parse_path_to_points(outer_path)
                
                if len(points) >= 3:  # Valid polygon
                    # Get parent group ID using parent_map
                    parent = self.parent_map.get(path_elem)
                    parent_id = None
                    feature_type = "obstacle"  # Default
                    
                    if parent is not None:
                        parent_id = parent.get('id')
                        # Classify based on group name
                        if parent_id and 'boundary' in parent_id.lower():
                            feature_type = "boundary"
                        elif parent_id and any(x in parent_id.lower() for x in ['object', 'obstacle', 'furniture']):
                            feature_type = "obstacle"
                    
                    self.geometries.append({
                        'points': points,
                        'original_path': d,
                        'cleaned_path': outer_path,
                        'parent_group': parent_id,
                        'feature_type': feature_type
                    })
                    
                    # Update the path element with cleaned data
                    path_elem.set('d', outer_path)
                    cleaned_count += 1
                    
            except Exception as e:
                print(f"⚠ Warning: Could not parse path: {e}")
                continue
        
        print(f"✓ Cleaned {cleaned_count} paths (removed doubled geometry)")
        
        # Print feature breakdown
        boundaries = sum(1 for g in self.geometries if g['feature_type'] == 'boundary')
        obstacles = sum(1 for g in self.geometries if g['feature_type'] == 'obstacle')
        print(f"  - {boundaries} boundary/boundaries")
        print(f"  - {obstacles} obstacle(s)")
        
        return self
    
    def _parse_path_to_points(self, path_string: str) -> List[Tuple[float, float]]:
        """
        Parse SVG path string to extract coordinate points.
        Handles M, L, H, V, Z commands (common in architectural drawings).
        """
        points = []
        current_x, current_y = 0.0, 0.0
        
        # Remove the command letter and split by command
        commands = re.findall(r'[MmLlHhVvZz][^MmLlHhVvZz]*', path_string)
        
        for cmd in commands:
            cmd_type = cmd[0]
            coords = cmd[1:].strip()
            
            # Extract numbers (including negative and decimals)
            numbers = re.findall(r'-?\d+\.?\d*', coords)
            numbers = [float(n) for n in numbers]
            
            if cmd_type in 'Mm':  # Move to
                if len(numbers) >= 2:
                    if cmd_type == 'M':  # Absolute
                        current_x, current_y = numbers[0], numbers[1]
                    else:  # Relative
                        current_x += numbers[0]
                        current_y += numbers[1]
                    points.append((current_x, current_y))
                    
                    # Remaining pairs are treated as line-to commands
                    for i in range(2, len(numbers), 2):
                        if i + 1 < len(numbers):
                            if cmd_type == 'M':
                                current_x, current_y = numbers[i], numbers[i+1]
                            else:
                                current_x += numbers[i]
                                current_y += numbers[i+1]
                            points.append((current_x, current_y))
            
            elif cmd_type in 'Ll':  # Line to
                for i in range(0, len(numbers), 2):
                    if i + 1 < len(numbers):
                        if cmd_type == 'L':  # Absolute
                            current_x, current_y = numbers[i], numbers[i+1]
                        else:  # Relative
                            current_x += numbers[i]
                            current_y += numbers[i+1]
                        points.append((current_x, current_y))
            
            elif cmd_type in 'Hh':  # Horizontal line
                for num in numbers:
                    if cmd_type == 'H':  # Absolute
                        current_x = num
                    else:  # Relative
                        current_x += num
                    points.append((current_x, current_y))
            
            elif cmd_type in 'Vv':  # Vertical line
                for num in numbers:
                    if cmd_type == 'V':  # Absolute
                        current_y = num
                    else:  # Relative
                        current_y += num
                    points.append((current_x, current_y))
            
            elif cmd_type in 'Zz':  # Close path
                # Don't add the closing point (we'll add it in GeoJSON conversion)
                pass
        
        # Remove duplicate consecutive points
        cleaned_points = []
        for point in points:
            if not cleaned_points or point != cleaned_points[-1]:
                cleaned_points.append(point)
        
        # Remove closing point if it duplicates the first
        if len(cleaned_points) > 1 and cleaned_points[0] == cleaned_points[-1]:
            cleaned_points = cleaned_points[:-1]
        
        return cleaned_points
    
    def save_svg(self, output_path: str) -> 'SVGFloorplanProcessor':
        """
        Save the cleaned SVG to a file.
        
        Args:
            output_path: Path where cleaned SVG will be saved
            
        Returns:
            self for method chaining
        """
        if self.tree is None:
            raise ValueError("No SVG loaded. Call import_svg() and clean_svg() first.")
        
        # Register namespace to avoid ns0 prefixes
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        
        self.tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"✓ Saved cleaned SVG to: {output_path}")
        
        return self
    
    def create_preview_svg(self, output_path: str, 
                          boundary_color: str = "#ff0000",
                          obstacle_color: str = "#000000",
                          stroke_width: float = 2,
                          fill: str = "none",
                          background: str = "#ffffff",
                          show_coordinates: bool = False) -> 'SVGFloorplanProcessor':
        """
        Create a visual preview SVG with color-coded boundaries and obstacles.
        
        Args:
            output_path: Path where preview SVG will be saved
            boundary_color: Color for boundary outlines (default: red)
            obstacle_color: Color for obstacle outlines (default: black)
            stroke_width: Width of the stroke
            fill: Fill color (default: "none" for transparent)
            background: Background color
            show_coordinates: If True, label vertices with coordinates
            
        Returns:
            self for method chaining
        """
        if not self.geometries:
            raise ValueError("No geometries to preview. Call clean_svg() first.")
        
        # Create new SVG
        svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': str(self.viewbox['width']),
            'height': str(self.viewbox['height']),
            'viewBox': f"{self.viewbox['x']} {self.viewbox['y']} {self.viewbox['width']} {self.viewbox['height']}"
        })
        
        # Add background
        bg = ET.SubElement(svg, 'rect', {
            'x': str(self.viewbox['x']),
            'y': str(self.viewbox['y']),
            'width': str(self.viewbox['width']),
            'height': str(self.viewbox['height']),
            'fill': background
        })
        
        # Add each geometry as a polygon
        for i, geom in enumerate(self.geometries):
            points_str = ' '.join([f"{x},{y}" for x, y in geom['points']])
            
            color = boundary_color if geom['feature_type'] == 'boundary' else obstacle_color
            
            polygon = ET.SubElement(svg, 'polygon', {
                'points': points_str,
                'fill': fill,
                'stroke': color,
                'stroke-width': str(stroke_width),
                'data-id': str(i),
                'data-type': geom['feature_type'],
                'data-group': geom['parent_group'] or 'none'
            })
            
            # Add coordinate labels if requested
            if show_coordinates:
                for j, (x, y) in enumerate(geom['points']):
                    text = ET.SubElement(svg, 'text', {
                        'x': str(x),
                        'y': str(y),
                        'font-size': '8',
                        'fill': color
                    })
                    text.text = f"({x:.1f},{y:.1f})"
        
        # Write to file
        tree = ET.ElementTree(svg)
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        print(f"✓ Created preview SVG: {output_path}")
        print(f"  Red = boundaries, Black = obstacles")
        
        return self
    
    def inspect_geometries(self, limit: int = 5):
        """
        Print detailed information about the extracted geometries.
        
        Args:
            limit: Maximum number of geometries to display in detail
        """
        if not self.geometries:
            print("No geometries to inspect. Call clean_svg() first.")
            return
        
        print("\n" + "="*60)
        print("GEOMETRY INSPECTION")
        print("="*60)
        
        for i, geom in enumerate(self.geometries[:limit]):
            print(f"\n{geom['feature_type'].upper()} {i}:")
            print(f"  Group: {geom['parent_group']}")
            print(f"  Points: {len(geom['points'])}")
            print(f"  Coordinates:")
            for j, (x, y) in enumerate(geom['points']):
                print(f"    [{j}] ({x:.2f}, {y:.2f})")
            
            # Calculate bounding box
            xs = [p[0] for p in geom['points']]
            ys = [p[1] for p in geom['points']]
            print(f"  BBox: ({min(xs):.2f}, {min(ys):.2f}) to ({max(xs):.2f}, {max(ys):.2f})")
            print(f"  Size: {max(xs)-min(xs):.2f} x {max(ys)-min(ys):.2f}")
        
        if len(self.geometries) > limit:
            print(f"\n... and {len(self.geometries) - limit} more geometries")
        
        print("="*60 + "\n")
        return self
    
    def convert_to_geojson(self, 
                           coordinate_system: str = "svg",
                           feature_properties: Optional[Dict] = None) -> 'SVGFloorplanProcessor':
        """
        Convert cleaned geometries to GeoJSON format.
        
        Args:
            coordinate_system: Either "svg" (origin top-left, +y down) or 
                             "cartesian" (origin bottom-left, +y up)
            feature_properties: Optional properties to add to each feature
            
        Returns:
            self for method chaining
        """
        if not self.geometries:
            raise ValueError("No geometries to convert. Call clean_svg() first.")
        
        features = []
        
        for i, geom in enumerate(self.geometries):
            # Transform coordinates if needed
            if coordinate_system == "cartesian":
                # Flip Y-axis: new_y = height - old_y
                points = [(x, self.viewbox['height'] - y) for x, y in geom['points']]
            else:
                points = geom['points']
            
            # GeoJSON expects closed polygon (first point repeated at end)
            coordinates = [points + [points[0]]]
            
            # Build properties
            props = {
                "type": geom['feature_type'],
                "id": i,
                "group": geom['parent_group'],
                "point_count": len(geom['points'])
            }
            
            # Add user-provided properties
            if feature_properties:
                props.update(feature_properties)
            
            feature = {
                "type": "Feature",
                "id": i,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates
                },
                "properties": props
            }
            
            features.append(feature)
        
        # Sort features: boundaries first, then obstacles
        features.sort(key=lambda f: (f['properties']['type'] != 'boundary', f['id']))
        
        # Build metadata
        coord_desc = ("top-left origin, +x right, +y down (SVG)" 
                     if coordinate_system == "svg" 
                     else "bottom-left origin, +x right, +y up (Cartesian)")
        
        self.geojson_data = {
            "type": "FeatureCollection",
            "metadata": {
                "source": "SVG floorplan",
                "viewBox": self.viewbox,
                "units": "pixels",
                "coordinate_system": coord_desc,
                "feature_counts": {
                    "boundaries": sum(1 for f in features if f['properties']['type'] == 'boundary'),
                    "obstacles": sum(1 for f in features if f['properties']['type'] == 'obstacle')
                }
            },
            "features": features
        }
        
        print(f"✓ Converted {len(features)} geometries to GeoJSON")
        print(f"  Coordinate system: {coordinate_system}")
        
        return self
    
    def export_geojson(self, output_path: str, indent: int = 2) -> 'SVGFloorplanProcessor':
        """
        Export GeoJSON data to a file.
        
        Args:
            output_path: Path where GeoJSON will be saved
            indent: JSON indentation level (default: 2)
            
        Returns:
            self for method chaining
        """
        if self.geojson_data is None:
            raise ValueError("No GeoJSON data to export. Call convert_to_geojson() first.")
        
        with open(output_path, 'w') as f:
            json.dump(self.geojson_data, f, indent=indent)
        
        print(f"✓ Exported GeoJSON to: {output_path}")
        return self
    
    def get_statistics(self) -> Dict:
        """Get statistics about the processed geometries."""
        if not self.geometries:
            return {"status": "No geometries loaded"}
        
        point_counts = [len(g['points']) for g in self.geometries]
        
        # Calculate bounding boxes
        all_x = []
        all_y = []
        for geom in self.geometries:
            for x, y in geom['points']:
                all_x.append(x)
                all_y.append(y)
        
        bbox = {
            "min_x": min(all_x) if all_x else 0,
            "max_x": max(all_x) if all_x else 0,
            "min_y": min(all_y) if all_y else 0,
            "max_y": max(all_y) if all_y else 0
        }
        
        return {
            "total_geometries": len(self.geometries),
            "boundaries": sum(1 for g in self.geometries if g['feature_type'] == 'boundary'),
            "obstacles": sum(1 for g in self.geometries if g['feature_type'] == 'obstacle'),
            "viewbox": self.viewbox,
            "bounding_box": bbox,
            "points_per_geometry": {
                "min": min(point_counts),
                "max": max(point_counts),
                "avg": sum(point_counts) / len(point_counts)
            },
            "groups": list(set(g['parent_group'] for g in self.geometries if g['parent_group']))
        }
    
    def print_summary(self):
        """Print a summary of the processed data."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("SVG PROCESSING SUMMARY")
        print("="*60)
        
        if "status" in stats:
            print(stats["status"])
            return
        
        print(f"Total Geometries: {stats['total_geometries']}")
        print(f"  - Boundaries: {stats['boundaries']}")
        print(f"  - Obstacles: {stats['obstacles']}")
        print(f"Canvas Size: {stats['viewbox']['width']:.2f} x {stats['viewbox']['height']:.2f}")
        print(f"Bounding Box: ({stats['bounding_box']['min_x']:.2f}, {stats['bounding_box']['min_y']:.2f}) to ({stats['bounding_box']['max_x']:.2f}, {stats['bounding_box']['max_y']:.2f})")
        print(f"Points per geometry: {stats['points_per_geometry']['min']}-{stats['points_per_geometry']['max']} (avg: {stats['points_per_geometry']['avg']:.1f})")
        
        if stats['groups']:
            print(f"Groups found: {', '.join(stats['groups'])}")
        
        print("="*60 + "\n")