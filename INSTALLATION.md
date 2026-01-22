# Installation Guide
Complete installation instructions for the Isovist Path Visualizer toolkit.

## Overview
This toolkit requires:
1. Python 3.8+ with dependencies
2. Compiled C++ visibility module
3. Supporting Python scripts

## **Python Environment Setup (Required)**

**IMPORTANT:** The pre-compiled visibility module binaries (`.so` and `.pyd` files) are built specifically for **Python 3.11.4**. They will **not work** with other Python versions.

### Setting Up Conda Environment

We strongly recommend using conda to create an isolated environment with the correct Python version:

```bash
# Create new conda environment with Python 3.11.4
conda create -n isovist python=3.11.4

# Activate the environment
conda activate isovist

# Verify Python version
python --version  # Should show: Python 3.11.4
```

**Every time you work with this toolkit**, activate the environment first:
```bash
conda activate isovist
```

### Why This Specific Version?

Python extension modules (`.so` on Linux/macOS, `.pyd` on Windows) are compiled against a specific Python version's ABI (Application Binary Interface). Using a different Python version will result in errors like:
- `ImportError: undefined symbol`
- `ImportError: DLL load failed`
- Version mismatch errors

If you need to use a different Python version, you must recompile the visibility module from source.

## Quick Install

```bash
# 1. Activate conda environment
conda activate isovist

# 2. Install Python dependencies
pip install svgwrite cairosvg

# 3. Verify installation
python -c "from visibility_module import get_visibility_module; print('✓ Module loaded')"
```

## Detailed Installation

### 1. Python Dependencies

**Required:**
```bash
pip install svgwrite
```

**Optional (for PNG export):**
```bash
pip install cairosvg
```

**System dependencies for cairosvg:**

**macOS:**
```bash
brew install cairo pkg-config
pip install cairosvg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libcairo2-dev pkg-config
pip install cairosvg
```

### 2. Verify Installation

Run this test to ensure everything is working:

```bash
python -c "
from visibility_module import get_visibility_module
vis = get_visibility_module()
print('✓ Visibility module loaded successfully')

# Test basic functionality
p = vis.module.Point(10.0, 20.0)
print(f'✓ Created test point: ({p.x}, {p.y})')
"
```

Expected output:
```
✓ Visibility polygon module loaded successfully
✓ Visibility module loaded successfully
✓ Created test point: (10.0, 20.0)
```

## Project Files Required

Your project directory should have:

```
your_project/
├── bindings.cpp                      # C++ bindings (pybind11)
├── VisibilityPolygon.cpp             # C++ implementation
├── VisibilityPolygon.h               # C++ header
├── clipper2/                         # Clipper2 library
│   └── include/
│       └── clipper2/
│           └── clipper.h
├── visibility_module.py              # Python wrapper
├── visibility_polygon.so             # Compiled module 
│
├── svg_to_json.py                   # Toolkit scripts
├── generate_reference_grid.py
├── path_creator.html
├── path_visualizer.py
└── SVGFloorplanProcessor.py
```

## Troubleshooting

### "ImportError: No module named 'visibility_polygon'"

**Cause:** Module not compiled or not in Python path

**Solution:**
```bash
# 1. Check if .so/.pyd file exists
ls visibility_polygon.*

# 2. Add to Python path if needed
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### "undefined symbol" or "cannot open shared library"

**Cause:** Module compiled with different Python version

**Solution:**
```bash
# Ensure you're using Python 3.11.4
conda activate isovist
python --version  # Must show Python 3.11.4

# Check module suffix expected
python -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"

# If you need to rebuild (requires source files and build tools):
python setup.py build_ext --inplace --force
```

### Wrong Python Version Active

**Symptoms:**
- Import errors despite correct files
- "version 'GLIBCXX_X.X.XX' not found"
- ABI compatibility errors

**Solution:**
```bash
# Deactivate current environment
conda deactivate

# Activate correct environment
conda activate isovist

# Verify version
python --version  # Must be 3.11.4
```

### cairosvg fails to install (macOS)

**Solution:**
```bash
# Install cairo via Homebrew
brew install cairo pkg-config

# Set PKG_CONFIG_PATH
export PKG_CONFIG_PATH="/usr/local/opt/cairo/lib/pkgconfig"

# Install cairosvg
pip install cairosvg
```

### cairosvg fails to install (Ubuntu)

**Solution:**
```bash
sudo apt-get install libcairo2-dev libgirepository1.0-dev
pip install cairosvg
```

## Verifying Your Installation

Run the complete workflow test:

```bash
# 0. Ensure correct environment is active
conda activate isovist

# 1. Check Python dependencies
python -c "import svgwrite; print('✓ svgwrite')"

# 2. Check visibility module
python -c "from visibility_module import get_visibility_module; get_visibility_module(); print('✓ visibility module')"

# 3. Test SVG conversion (requires sample.svg)
python svg_to_json.py sample.svg test.geojson

# 4. Test reference grid
python generate_reference_grid.py test.geojson test_ref.svg

# 5. Test visualizer (requires paths.json)
python path_visualizer.py test.geojson paths.json --output-dir test_output
```

## Next Steps

After successful installation:
1. Read [README.md](__README.md__) for usage instructions
2. Try the example workflow with sample data
3. Create your own floorplan visualizations

## License
MIT