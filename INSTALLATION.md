# Installation Guide

Complete installation instructions for the Isovist Path Visualizer toolkit.

## Overview

This toolkit requires:
1. Python 3.8+ with dependencies
2. Compiled C++ visibility module
3. Supporting Python scripts

## Quick Install

```bash
# 1. Install Python dependencies
pip install svgwrite cairosvg

# 2. Compile C++ module (see below)
python setup.py build_ext --inplace

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

**Windows:**
- Download GTK+ runtime from https://www.gtk.org/download/windows.php
- Or use Windows Subsystem for Linux (WSL)

### 2. C++ Compiler Setup

You need a C++ compiler to build the visibility polygon module.

**macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install build-essential python3-dev cmake
```

**Windows:**
- Install Visual Studio (Community Edition is free)
- Include "Desktop development with C++" workload
- Or install Build Tools for Visual Studio

### 3. Compile C++ Visibility Module

#### Prerequisites

Install pybind11:
```bash
pip install pybind11
```

#### Option A: Using setup.py (Recommended)

Create `setup.py` in your project directory:

```python
from setuptools import setup, Extension
from pybind11.setup_helpers import Pybind11Extension, build_ext
import sys

ext_modules = [
    Pybind11Extension(
        "visibility_polygon",
        ["bindings.cpp", "VisibilityPolygon.cpp"],
        include_dirs=[".", "./clipper2/include"],
        extra_compile_args=["-std=c++17"],
        define_macros=[("VERSION_INFO", "1.0.0")],
    ),
]

setup(
    name="visibility_polygon",
    version="1.0.0",
    author="Your Name",
    description="Visibility polygon computation library",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.8",
)
```

Then compile:
```bash
python setup.py build_ext --inplace
```

**Output:** You'll get a file like:
- macOS: `visibility_polygon.cpython-311-darwin.so`
- Linux: `visibility_polygon.cpython-311-x86_64-linux-gnu.so`
- Windows: `visibility_polygon.cp311-win_amd64.pyd`

#### Option B: Manual Compilation

**macOS/Linux:**
```bash
# Get Python include path
PYTHON_INCLUDE=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")

# Get pybind11 include path
PYBIND_INCLUDE=$(python3 -m pybind11 --includes)

# Get extension suffix
EXT_SUFFIX=$(python3-config --extension-suffix)

# Compile
g++ -O3 -Wall -shared -std=c++17 -fPIC \
    $PYBIND_INCLUDE \
    -I. -I./clipper2/include \
    bindings.cpp VisibilityPolygon.cpp \
    -o visibility_polygon${EXT_SUFFIX}
```

**Windows (Visual Studio Command Prompt):**
```cmd
cl /O2 /std:c++17 /LD ^
   /I"C:\path\to\pybind11\include" ^
   /I"C:\Python311\include" ^
   /I".\clipper2\include" ^
   bindings.cpp VisibilityPolygon.cpp ^
   /link /OUT:visibility_polygon.pyd
```

### 4. Verify Installation

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
├── visibility_polygon.so             # Compiled module (after build)
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

# 2. Recompile if missing
python setup.py build_ext --inplace

# 3. Add to Python path if needed
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### "undefined symbol" or "cannot open shared library"

**Cause:** Module compiled with different Python version

**Solution:**
```bash
# Check your Python version
python --version

# Check module suffix expected
python -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"

# Rebuild with correct version
python setup.py build_ext --inplace --force
```

### Compilation fails with "pybind11/pybind11.h: No such file"

**Cause:** pybind11 not installed

**Solution:**
```bash
pip install pybind11
```

### Compilation fails with C++17 errors

**Cause:** Compiler doesn't support C++17

**Solution:**

**macOS:**
```bash
# Update Xcode Command Line Tools
xcode-select --install
```

**Ubuntu/Debian:**
```bash
# Install newer g++
sudo apt-get install g++-9
export CXX=g++-9
python setup.py build_ext --inplace
```

**Windows:**
- Ensure Visual Studio 2017 or newer is installed

### Module loads but functions not found

**Cause:** Bindings not properly exposed

**Solution:**
Check that `bindings.cpp` properly exposes all required functions:
- `compute_visibility_polygon`
- `Point` class
- `Polygon2` class

Rebuild after verifying bindings:
```bash
python setup.py build_ext --inplace --force
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

## Platform-Specific Notes

### macOS Apple Silicon (M1/M2/M3)

You may need to specify architecture:
```bash
arch -arm64 python setup.py build_ext --inplace
```

Or for Intel compatibility:
```bash
arch -x86_64 python setup.py build_ext --inplace
```

### Windows with MinGW

If using MinGW instead of Visual Studio:
```bash
python setup.py build_ext --inplace --compiler=mingw32
```

### Linux without root access

Install dependencies in user directory:
```bash
# Install pybind11 locally
pip install --user pybind11

# Compile with user paths
python setup.py build_ext --inplace
```

## Verifying Your Installation

Run the complete workflow test:

```bash
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

## Development Setup

For development work:

```bash
# Clone repository
git clone https://github.com/your-username/isovist_path_visualizer.git
cd isovist_path_visualizer

# Install in development mode
pip install -e .

# Install dev dependencies
pip install pytest black mypy

# Run tests
pytest tests/

# Format code
black *.py
```

## Docker Installation (Optional)

For a containerized environment:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python setup.py build_ext --inplace

CMD ["python", "path_visualizer.py", "--help"]
```

Build and run:
```bash
docker build -t isovist-visualizer .
docker run -v $(pwd)/data:/app/data isovist-visualizer \
    python path_visualizer.py data/floorplan.geojson data/paths.json
```

## Getting Help

If installation fails:

1. **Check Python version:** Must be 3.8 or higher
   ```bash
   python --version
   ```

2. **Check compiler:** Must support C++17
   ```bash
   g++ --version  # Linux/macOS
   cl           # Windows (in VS Command Prompt)
   ```

3. **Check file structure:** Ensure all source files are present
   ```bash
   ls *.cpp *.h
   ls -R clipper2/
   ```

4. **Enable verbose output:**
   ```bash
   python setup.py build_ext --inplace --verbose
   ```

5. **Check GitHub Issues:** https://github.com/brn-cntrl/isovist_path_visualizer/issues

## Next Steps

After successful installation:

1. Read [README.md](README.md) for usage instructions
2. Try the example workflow with sample data
3. Create your own floorplan visualizations

## License

MIT