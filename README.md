# Isovist Path Visualizer

Generate visibility polygon (isovist) visualizations along pedestrian paths through architectural floorplans.

## Overview

This toolkit processes SVG floorplans and creates sequences of images showing what's visible from each point along a path. Perfect for analyzing wayfinding, spatial perception, and architectural visibility in buildings.

**Key Features:**
- Convert SVG floorplans to GeoJSON format
- Create pedestrian paths with interactive browser tool
- Generate isovist visualizations at each point along paths
- Output as SVG or PNG sequences
- Grayscale, publication-ready graphics

## Requirements

### Python Dependencies
```bash
pip install svgwrite cairosvg  # cairosvg optional for PNG export
```

### C++ Visibility Module
You need the compiled visibility polygon module:
- **macOS:** `visibility_polygon.cpython-311-darwin.so`
- **Windows:** `visibility_polygon.cp311-win_amd64.pyd`
- **Linux:** `visibility_polygon.cpython-311-x86_64-linux-gnu.so`

Plus the Python wrapper: `visibility_module.py`

*(Compilation instructions for the C++ module are in INSTALLATION.md)*

## Quick Start

### Complete Workflow

```bash
# 1. Convert SVG floorplan to GeoJSON
python svg_to_json.py floorplan.svg floorplan.geojson

# 2. Generate reference grid for path creation
python generate_reference_grid.py floorplan.geojson reference.svg

# 3. Create paths (open in browser)
# Open path_creator.html → Load reference.svg → Create paths → Export paths.json

# 4. Generate isovist visualizations
python path_visualizer.py floorplan.geojson paths.json --format both --output-dir ./output
```

## Detailed Workflow

### Step 1: Convert SVG to GeoJSON

Convert your architectural floorplan from SVG to GeoJSON format:

```bash
python svg_to_json.py floorplan.svg floorplan.geojson
```

**Input:** SVG file with polygons representing walls and obstacles  
**Output:** GeoJSON file with Cartesian coordinate system (bottom-left origin)

**Requirements for SVG:**
- Walls/obstacles should be closed polygons or paths
- Can contain multiple layers or groups
- Will be automatically cleaned and simplified

### Step 2: Generate Reference Grid

Create a reference grid to help with path creation:

```bash
python generate_reference_grid.py floorplan.geojson reference.svg
```

**Optional parameters:**
```bash
# Custom output filename
python generate_reference_grid.py floorplan.geojson my_reference.svg

# Custom grid spacing (default: 10 pixels)
python generate_reference_grid.py floorplan.geojson reference.svg 20.0
```

**Output:** SVG file with:
- Floorplan geometry
- Grid lines every N pixels
- Coordinate labels on axes
- Easy-to-read reference for clicking precise locations

### Step 3: Create Paths

Use the interactive browser tool to create pedestrian paths:

1. **Open** `path_creator.html` in your web browser
2. **Load** the reference grid SVG (from Step 2)
3. **Enter** a path ID (e.g., "path1", "main_corridor", "visitor_route")
4. **Click** "New Path"
5. **Click** points on the canvas to create waypoints
   - Points snap to grid (10-pixel increments)
   - See Cartesian coordinates in status bar
6. **Click** "Finish Path" when done
7. **Repeat** for additional paths
8. **Click** "Export JSON" to save

**Path Creator Controls:**
- **New Path** - Start creating a new path
- **Finish Path** - Complete current path
- **Undo Point** - Remove last point
- **Cancel Path** - Discard current path
- **Zoom slider** - Adjust view scale (50%-300%)
- **Export JSON** - Save all paths to `paths.json`

**Tips:**
- Create multiple paths in one session
- Paths automatically saved with unique IDs
- Grid snapping ensures aligned coordinates
- Use zoom for precision in complex areas

### Step 4: Generate Visualizations

Generate isovist visualizations along your paths:

```bash
# Basic usage (SVG output)
python path_visualizer.py floorplan.geojson paths.json

# PNG output
python path_visualizer.py floorplan.geojson paths.json --format png

# Both SVG and PNG
python path_visualizer.py floorplan.geojson paths.json --format both

# Custom output directory
python path_visualizer.py floorplan.geojson paths.json --output-dir ./my_renders

# Specific path only
python path_visualizer.py floorplan.geojson paths.json --path-id path1
```

**Output:** For each point in the path:
- Floorplan with obstacles (gray polygons)
- Visibility polygon/isovist (light gray fill)
- Complete path line (gray)
- Past waypoints (medium gray circles)
- Current viewpoint (black circle, larger)
- Future waypoints (light gray circles)

**File naming:** `{path_id}_point_{index}.svg` (e.g., `path1_point_000.svg`, `path1_point_001.svg`, ...)

## Command Reference

### svg_to_json.py
```bash
python svg_to_json.py INPUT.svg [OUTPUT.geojson]
```
Converts SVG floorplan to GeoJSON format with Cartesian coordinates.

### generate_reference_grid.py
```bash
python generate_reference_grid.py INPUT.geojson [OUTPUT.svg] [GRID_SPACING]
```
Creates reference grid SVG with coordinate labels.

**Arguments:**
- `INPUT.geojson` - GeoJSON floorplan from Step 1
- `OUTPUT.svg` - Output filename (default: `{input}_reference.svg`)
- `GRID_SPACING` - Grid spacing in pixels (default: 10.0)

### path_visualizer.py
```bash
python path_visualizer.py FLOORPLAN.geojson PATHS.json [OPTIONS]
```

**Arguments:**
- `FLOORPLAN.geojson` - Floorplan GeoJSON file
- `PATHS.json` - Paths JSON file from path_creator.html

**Options:**
- `--path-id ID` - Process specific path only (default: all paths)
- `--output-dir DIR` - Output directory (default: `./output`)
- `--format {svg,png,both}` - Output format (default: `svg`)

**Examples:**
```bash
# All paths, SVG only
python path_visualizer.py floorplan.geojson paths.json

# Specific path, PNG only
python path_visualizer.py floorplan.geojson paths.json --path-id path1 --format png

# All paths, both formats, custom directory
python path_visualizer.py floorplan.geojson paths.json --format both --output-dir ./renders
```

## File Formats

### Input: SVG Floorplan
Standard SVG file with:
- Closed polygon paths representing walls/obstacles
- Any standard SVG structure (groups, layers, etc.)
- Will be automatically processed and cleaned

### Intermediate: GeoJSON Floorplan
```json
{
  "type": "FeatureCollection",
  "metadata": {
    "viewBox": {"x": 0, "y": 0, "width": 675.59, "height": 307.14},
    "coordinate_system": "bottom-left origin, +x right, +y up (Cartesian)"
  },
  "features": [
    {
      "type": "Feature",
      "properties": {"type": "boundary", "id": 0},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[x1, y1], [x2, y2], ...]]
      }
    }
  ]
}
```

### Intermediate: Paths JSON
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "id": "path1",
        "type": "trajectory",
        "point_count": 13
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [[x1, y1], [x2, y2], ...]
      }
    }
  ]
}
```

### Output: Isovist Visualizations
- **SVG:** Vector graphics, scalable, editable
- **PNG:** Raster images at 150 DPI, ready for publication

## Creating Animations (Optional)

Convert your image sequence to animated GIF or video:

### GIF Animation (ImageMagick)
```bash
convert -delay 50 -loop 0 output/path1_point_*.png output/path1_animation.gif
```

### MP4 Video (FFmpeg)
```bash
ffmpeg -framerate 10 -pattern_type glob -i 'output/path1_point_*.png' \
       -c:v libx264 -pix_fmt yuv420p output/path1_animation.mp4
```

## Coordinate Systems

**Critical:** All tools use consistent coordinate systems:

- **SVG Input:** Standard SVG coordinates (top-left origin, +y down)
- **GeoJSON:** Cartesian coordinates (bottom-left origin, +y up)
- **Path Creator:** Cartesian coordinates matching GeoJSON
- **Visualizer Output:** SVG coordinates (automatically converted)

Conversions are handled automatically - you don't need to worry about this!

## Troubleshooting

### "Visibility module not found"
Make sure you have:
1. Compiled C++ module (`visibility_polygon.so` or `.pyd`)
2. Python wrapper (`visibility_module.py`)
3. Both in the same directory as scripts or in `PYTHONPATH`

### "Path coordinates don't align with floorplan"
1. Verify you loaded the **reference grid** (not original SVG) in path_creator.html
2. Check that `floorplanHeight` is detected correctly (see browser console)
3. Regenerate reference grid if needed

### "No obstacles found in floorplan"
Check that your SVG has closed polygon shapes. The converter looks for:
- `<polygon>` elements
- `<path>` elements with closed paths
- Grouped shapes in layers

### PNG export fails
Install cairo dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install libcairo2-dev
pip install cairosvg

# macOS
brew install cairo
pip install cairosvg
```

## Color Scheme

The visualizer uses grayscale colors suitable for publication:

| Element | Color |
|---------|-------|
| Boundary | Dark gray dashed line |
| Obstacles | Light gray fill, dark outline |
| Isovist | Light gray fill with transparency |
| Path line | Medium gray |
| Current point | Black (emphasized) |
| Past points | Medium gray |
| Future points | Light gray |

## Performance

Typical processing time on modern hardware:
- SVG to GeoJSON: < 1 second
- Reference grid generation: < 1 second  
- Path creation: Interactive, instant feedback
- Isovist visualization: ~0.5-2 seconds per point
  - 20-point path: ~10-40 seconds total

## Advanced Usage

### Batch Processing Multiple Floorplans
```bash
#!/bin/bash
for svg in floorplans/*.svg; do
    base=$(basename "$svg" .svg)
    python svg_to_json.py "$svg" "output/${base}.geojson"
    python generate_reference_grid.py "output/${base}.geojson" "output/${base}_ref.svg"
done
```

### Processing Multiple Paths
```bash
# Process each path separately
for path_id in path1 path2 path3; do
    python path_visualizer.py floorplan.geojson paths.json \
        --path-id "$path_id" \
        --output-dir "./output/${path_id}" \
        --format both
done
```

## Project Structure

```
your_project/
├── svg_to_json.py                    # SVG → GeoJSON converter
├── generate_reference_grid.py        # Reference grid generator
├── path_creator.html                 # Interactive path creator
├── path_visualizer.py                # Isovist visualizer
├── visibility_module.py              # Python wrapper for C++ module
├── visibility_polygon.so             # Compiled C++ module
├── SVGFloorplanProcessor.py          # SVG processing utilities
│
├── floorplan.svg                     # Your input floorplan
├── floorplan.geojson                 # Converted floorplan
├── reference.svg                     # Reference grid for path creation
├── paths.json                        # Created paths
│
└── output/                           # Generated visualizations
    ├── path1_point_000.svg
    ├── path1_point_001.svg
    └── ...
```

## Contributing

Issues and pull requests welcome! Please ensure:
- Code follows existing style
- Coordinate system conventions are maintained
- Examples are tested with provided sample data

## License

MIT

## Citation

If you use this tool in academic work, please cite:

```
Cantrell, B. PhD, Gephstein, S. PhD
```

## Acknowledgments

- Visibility polygon computation based on ray-casting algorithm
- Uses Clipper2 library for polygon operations
- Built with pybind11 for Python/C++ integration

## Support

- **Issues:** [GitHub Issues](isovist_path_visualizer/issues)
- **Documentation:** See individual script files for detailed API docs
- **Examples:** Sample floorplans and paths in `/examples` directory

---

**Version:** 1.0.0  
**Last Updated:** January 2026