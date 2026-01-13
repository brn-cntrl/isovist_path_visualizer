#!/usr/bin/env python3
"""
GeoJSON Structure Inspector

Analyzes a GeoJSON file to understand its structure and help diagnose issues.
"""

import json
import sys
from collections import defaultdict

def inspect_geojson(filepath: str):
    """Inspect and display GeoJSON structure"""
    
    print("=" * 70)
    print(f"GeoJSON Inspector: {filepath}")
    print("=" * 70)
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return
    
    print("\n1. TOP LEVEL STRUCTURE")
    print("-" * 70)
    print(f"Type: {data.get('type', 'NOT FOUND')}")
    print(f"Top-level keys: {list(data.keys())}")
    print("\n2. METADATA")
    print("-" * 70)
    if 'metadata' in data:
        metadata = data['metadata']
        print(f"Metadata keys: {list(metadata.keys())}")
        
        if 'viewBox' in metadata:
            vb = metadata['viewBox']
            print(f"ViewBox: {vb}")
            if isinstance(vb, dict):
                width = vb.get('width', 'N/A')
                height = vb.get('height', 'N/A')
                print(f"  Dimensions: {width} x {height}")
        
        if 'coordinate_system' in metadata:
            print(f"Coordinate System: {metadata['coordinate_system']}")
    else:
        print("No metadata found")
    
    print("\n3. FEATURES")
    print("-" * 70)
    features = data.get('features', [])
    print(f"Total features: {len(features)}")
    
    if not features:
        print("WARNING: No features found!")
        return
    
    print("\n4. FEATURE STRUCTURE ANALYSIS")
    print("-" * 70)
    
    property_structures = defaultdict(list)
    geometry_types = defaultdict(int)
    
    for i, feature in enumerate(features):
        geom_type = feature.get('geometry', {}).get('type', 'UNKNOWN')
        geometry_types[geom_type] += 1
        props = feature.get('properties', {})
        prop_keys = tuple(sorted(props.keys()))
        property_structures[prop_keys].append(i)
    
    print("Geometry types:")
    for geom_type, count in geometry_types.items():
        print(f"  - {geom_type}: {count}")
    
    print("\nProperty structures:")
    for prop_keys, indices in property_structures.items():
        if prop_keys:
            print(f"  - Keys: {list(prop_keys)}")
            print(f"    Count: {len(indices)}")
            print(f"    Feature indices: {indices[:5]}{'...' if len(indices) > 5 else ''}")
        else:
            print(f"  - No properties")
            print(f"    Count: {len(indices)}")
    
    print("\n5. SAMPLE FEATURES")
    print("-" * 70)
    
    samples = min(3, len(features))
    for i in range(samples):
        feature = features[i]
        print(f"\nFeature {i}:")
        print(f"  Keys: {list(feature.keys())}")
        
        if 'id' in feature:
            print(f"  ID: {feature['id']}")
        
        if 'properties' in feature:
            props = feature['properties']
            print(f"  Properties: {props}")
        else:
            print("  Properties: NONE")
        
        if 'geometry' in feature:
            geom = feature['geometry']
            print(f"  Geometry type: {geom.get('type', 'UNKNOWN')}")
            if 'coordinates' in geom:
                coords = geom['coordinates']
                if isinstance(coords, list) and len(coords) > 0:
                    if isinstance(coords[0], list) and len(coords[0]) > 0:
                        point_count = len(coords[0])
                        print(f"  Point count: {point_count}")
                        if point_count > 0:
                            print(f"  First point: {coords[0][0]}")
                        if point_count > 1:
                            print(f"  Second point: {coords[0][1]}")
    
    print("\n6. POTENTIAL ISSUES")
    print("-" * 70)
    
    issues = []
    
    features_without_type = 0
    for feature in features:
        props = feature.get('properties', {})
        if 'type' not in props:
            features_without_type += 1
    
    if features_without_type > 0:
        issues.append(f"{features_without_type} features don't have 'type' in properties")
    
    features_without_props = sum(1 for f in features if 'properties' not in f)
    if features_without_props > 0:
        issues.append(f"{features_without_props} features have no 'properties' field")
    
    features_without_coords = 0
    for feature in features:
        geom = feature.get('geometry', {})
        if 'coordinates' not in geom or not geom['coordinates']:
            features_without_coords += 1
    
    if features_without_coords > 0:
        issues.append(f"{features_without_coords} features have no coordinates")
    
    if issues:
        for issue in issues:
            print(f"⚠️  {issue}")
    else:
        print("✓ No obvious issues detected")
    
    print("\n7. RECOMMENDATIONS FOR VISUALIZER")
    print("-" * 70)
    
    if features_without_type > 0:
        print("Your GeoJSON features don't all have 'type' in properties.")
        print("The visualizer now handles this - it will include all Polygon features.")
        print("✓ Updated visualizer should work with your file.")
    else:
        print("✓ All features have 'type' property - should work fine.")
    
    coord_system = data.get('metadata', {}).get('coordinate_system', 'UNKNOWN')
    if 'bottom-left' in coord_system.lower() or 'cartesian' in coord_system.lower():
        print("✓ Coordinate system is Cartesian (bottom-left origin) - correct!")
    else:
        print(f"⚠️  Coordinate system: {coord_system}")
        print("   Expected: Cartesian with bottom-left origin")
    
    print("\n" + "=" * 70)

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_geojson.py <file.geojson>")
        print("\nExample:")
        print("  python inspect_geojson.py floorplan.geojson")
        sys.exit(1)
    
    filepath = sys.argv[1]
    inspect_geojson(filepath)

if __name__ == "__main__":
    main()