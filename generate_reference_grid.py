#!/usr/bin/env python3
import json
import sys
from xml.etree.ElementTree import Element, SubElement, ElementTree


def generate_reference_grid(geojson_path: str, output_path: str,
                           grid_spacing: float = 10.0,
                           show_coordinates: bool = True):
    """
    Generate a reference grid SVG with coordinate labels.
    
    Args:
        geojson_path: Path to the floorplan GeoJSON
        output_path: Path for output SVG
        grid_spacing: Distance between grid lines
        show_coordinates: Whether to show coordinate labels
    """
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    features = data.get('features', [])
    viewbox = metadata.get('viewBox', {})
    
    min_x = viewbox.get('x', 0)
    min_y = viewbox.get('y', 0)
    width = viewbox.get('width', 800)
    height = viewbox.get('height', 600)
    max_x = min_x + width
    max_y = min_y + height
    
    label_padding = 30

    svg = Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': str(width + label_padding),
        'height': str(height + label_padding),
        'viewBox': f"{min_x - label_padding} {min_y} {width + label_padding} {height + label_padding}"
    })
    
    SubElement(svg, 'rect', {
        'x': str(min_x - label_padding),
        'y': str(min_y),
        'width': str(label_padding),
        'height': str(height),
        'fill': '#ffffff'
    })

    SubElement(svg, 'rect', {
        'x': str(min_x - label_padding),
        'y': str(max_y),
        'width': str(width + label_padding),
        'height': str(label_padding),
        'fill': '#ffffff'
    })
   
    SubElement(svg, 'rect', {
        'x': str(min_x),
        'y': str(min_y),
        'width': str(width),
        'height': str(height),
        'fill': '#ffffff'
    })
    
    grid_group = SubElement(svg, 'g', {'id': 'grid', 'opacity': '0.3'})

    x = min_x
    while x <= max_x:
        SubElement(grid_group, 'line', {
            'x1': str(x),
            'y1': str(min_y),
            'x2': str(x),
            'y2': str(max_y),
            'stroke': '#cccccc' if x % (grid_spacing * 2) != 0 else '#999999',
            'stroke-width': '1' if x % (grid_spacing * 2) != 0 else '2'
        })
        x += grid_spacing

    y = min_y
    while y <= max_y:
        SubElement(grid_group, 'line', {
            'x1': str(min_x),
            'y1': str(y),
            'x2': str(max_x),
            'y2': str(y),
            'stroke': '#cccccc' if y % (grid_spacing * 2) != 0 else '#999999',
            'stroke-width': '1' if y % (grid_spacing * 2) != 0 else '2'
        })
        y += grid_spacing
    
    if show_coordinates:
        labels_group = SubElement(svg, 'g', {'id': 'labels'})
        
        x = min_x
        while x <= max_x:
            if x % (grid_spacing * 2) == 0:  # Only label major gridlines
                SubElement(labels_group, 'rect', {
                    'x': str(x - 15),
                    'y': str(max_y + 10),
                    'width': '40',
                    'height': '14',
                    'fill': 'white',
                    'stroke': 'none'
                })
                text = SubElement(labels_group, 'text', {
                    'x': str(x),
                    'y': str(max_y + 20),
                    'font-size': '6',
                    'font-family': 'monospace',
                    'fill': '#333333',
                    'text-anchor': 'middle'
                })
                text.text = f"{x:.0f}"
            x += grid_spacing
        
        cartesian_y = 0
        while cartesian_y <= height:
            if cartesian_y % (grid_spacing * 2) == 0:
                svg_y = height - cartesian_y
                
                SubElement(labels_group, 'rect', {
                    'x': str(min_x - 25),
                    'y': str(svg_y - 6),
                    'width': '20',
                    'height': '16',
                    'fill': 'white',
                    'stroke': 'none'
                })
                text = SubElement(labels_group, 'text', {
                    'x': str(min_x - 5),
                    'y': str(svg_y + 3),
                    'font-size': '6',
                    'font-family': 'monospace',
                    'fill': '#333333',
                    'text-anchor': 'end'
                })
                text.text = f"{int(cartesian_y)}"
            cartesian_y += grid_spacing

    floorplan_group = SubElement(svg, 'g', {'id': 'floorplan'})
    
    for feature in features:
        if feature['properties']['type'] == 'boundary':
            coords = feature['geometry']['coordinates'][0]
            points = ' '.join([f"{x},{height - y}" for x, y in coords])
            SubElement(floorplan_group, 'polygon', {
                'points': points,
                'fill': 'none',
                'stroke': '#ff0000',
                'stroke-width': '3',
                'stroke-dasharray': '5,5'
            })

    for feature in features:
        if feature['properties']['type'] == 'obstacle':
            coords = feature['geometry']['coordinates'][0]
            points = ' '.join([f"{x},{height - y}" for x, y in coords])
            SubElement(floorplan_group, 'polygon', {
                'points': points,
                'fill': '#e0e0e0',
                'stroke': '#333333',
                'stroke-width': '2'
            })
            
            obstacle_id = feature['properties']['id']
            
            svg_coords = [(x, height - y) for x, y in coords]
            min_x = min(x for x, y in svg_coords)
            min_svg_y = min(y for x, y in svg_coords)
            
            label_x = min_x + 3
            label_y = min_svg_y + 10
            
            SubElement(floorplan_group, 'rect', {
                'x': str(label_x - 2),
                'y': str(label_y - 9),
                'width': '14',
                'height': '11',
                'fill': 'white',
                'opacity': '0.8',
                'stroke': 'none'
            })
            
            text = SubElement(floorplan_group, 'text', {
                'x': str(label_x),
                'y': str(label_y),
                'font-size': '9',
                'font-family': 'monospace',
                'font-weight': 'bold',
                'fill': '#000000',
                'text-anchor': 'start'
            })
            text.text = str(obstacle_id)
    
    tree = ElementTree(svg)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"Generated reference grid: {output_path}")
    print(f"Grid spacing: {grid_spacing}")
    print(f"Dimensions: {width} x {height}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_reference_grid.py <floorplan.geojson> [output.svg] [grid_spacing]")
        print("\nExample:")
        print("python generate_reference_grid.py floorplan.geojson")
        print("python generate_reference_grid.py floorplan.geojson reference.svg 25.0")
        sys.exit(1)
    
    geojson_path = sys.argv[1]
    
    import os
    base = os.path.splitext(geojson_path)[0]
    output_path = sys.argv[2] if len(sys.argv) >= 3 else f"{base}_reference.svg"
    
    grid_spacing = float(sys.argv[3]) if len(sys.argv) >= 4 else 10.0
    
    generate_reference_grid(geojson_path, output_path, grid_spacing)
    print(f"\nOpen {output_path} in a browser to see coordinates.")

if __name__ == "__main__":
    main()