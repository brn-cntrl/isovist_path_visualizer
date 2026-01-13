#!/usr/bin/env python3
"""Simple SVG to GeoJSON converter"""

import sys
from SVGFloorplanProcessor import SVGFloorplanProcessor

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_svg.py input.svg [output.geojson]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.svg', '.geojson')
    
    processor = SVGFloorplanProcessor()
    processor.import_svg(input_file)\
             .clean_svg()\
             .convert_to_geojson(coordinate_system="cartesian")\
             .export_geojson(output_file)