#!/usr/bin/env python3
"""
Setup verification and testing script for path_visualizer.py

This script checks that all required components are present and working.
"""

import sys
import os
import platform

def check_python_version():
    """Check Python version"""
    print("\n" + "="*60)
    print("1. Python Version Check")
    print("="*60)
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 8:
        print("✓ Python version is compatible (3.8+)")
        return True
    else:
        print("✗ Python 3.8+ required")
        return False

def check_dependencies():
    """Check required Python packages"""
    print("\n" + "="*60)
    print("2. Python Dependencies Check")
    print("="*60)
    
    deps = {
        'svgwrite': 'pip install svgwrite',
        'cairosvg': 'pip install cairosvg (optional, for PNG export)'
    }
    
    all_good = True
    for module_name, install_cmd in deps.items():
        try:
            __import__(module_name)
            print(f"✓ {module_name} installed")
        except ImportError:
            optional = "optional" in install_cmd
            symbol = "!" if optional else "✗"
            print(f"{symbol} {module_name} not found - {install_cmd}")
            if not optional:
                all_good = False
    
    return all_good

def check_visibility_module():
    """Check visibility module and C++ extension"""
    print("\n" + "="*60)
    print("3. Visibility Module Check")
    print("="*60)
    
    system = platform.system()
    py_version = f"{sys.version_info.major}{sys.version_info.minor}"
    
    print(f"OS: {system}")
    print(f"Expected C++ extension file:")
    
    if system == "Darwin":
        expected = f"visibility_polygon.cpython-{py_version}-darwin.so"
    elif system == "Windows":
        expected = f"visibility_polygon.cp{py_version}-win_amd64.pyd"
    elif system == "Linux":
        expected = f"visibility_polygon.cpython-{py_version}-x86_64-linux-gnu.so"
    else:
        expected = "visibility_polygon.so"
    
    print(f"  {expected}")
    
    # Check for Python wrapper
    wrapper_found = False
    if os.path.exists('visibility_module.py'):
        print("✓ visibility_module.py found")
        wrapper_found = True
    elif os.path.exists('visibility_loader.py'):
        print("✓ visibility_loader.py found")
        wrapper_found = True
    else:
        print("✗ No visibility_module.py or visibility_loader.py found")
    
    # Check for C++ extension
    current_dir = os.getcwd()
    extension_files = [f for f in os.listdir(current_dir) 
                      if f.startswith('visibility_polygon') and (f.endswith('.so') or f.endswith('.pyd'))]
    
    if extension_files:
        print(f"✓ C++ extension found: {extension_files}")
    else:
        print("✗ No C++ extension (.so/.pyd) found in current directory")
        print("  You need to compile the C++ module first")
        return False
    
    # Try to actually import it
    try:
        from visibility_module import get_visibility_module
        vis = get_visibility_module()
        print("✓ Successfully imported and initialized visibility module")
        
        # Test basic functionality
        test_point = vis.module.Point(10.0, 20.0)
        print(f"✓ Created test Point: ({test_point.x}, {test_point.y})")
        
        return True
    except ImportError as e:
        try:
            from visibility_loader import load_visibility_module
            vp = load_visibility_module()
            print("✓ Successfully loaded via visibility_loader.py")
            return True
        except ImportError as e2:
            print(f"✗ Failed to import visibility module: {e}")
            return False
    except Exception as e:
        print(f"✗ Error testing visibility module: {e}")
        return False

def check_sample_files():
    """Check for sample data files"""
    print("\n" + "="*60)
    print("4. Sample Data Files Check")
    print("="*60)
    
    files_to_check = [
        ('floorplan.geojson', 'Floorplan GeoJSON file'),
        ('paths.json', 'Paths JSON file'),
    ]
    
    all_found = True
    for filename, description in files_to_check:
        if os.path.exists(filename):
            print(f"✓ {filename} found - {description}")
        else:
            print(f"! {filename} not found - {description}")
            all_found = False
    
    if not all_found:
        print("\nTo create sample files:")
        print("  1. Convert SVG: python svg_to_json.py floorplan.svg floorplan.geojson")
        print("  2. Create paths: Open path_creator.html in browser")
    
    return all_found

def check_visualizer_script():
    """Check if visualizer script exists"""
    print("\n" + "="*60)
    print("5. Visualizer Script Check")
    print("="*60)
    
    if os.path.exists('path_visualizer.py'):
        print("✓ path_visualizer.py found")
        
        # Make it executable
        import stat
        st = os.stat('path_visualizer.py')
        os.chmod('path_visualizer.py', st.st_mode | stat.S_IEXEC)
        print("✓ Made executable")
        
        return True
    else:
        print("✗ path_visualizer.py not found")
        return False

def run_sample_test():
    """Run a minimal test if sample files exist"""
    print("\n" + "="*60)
    print("6. Running Sample Test")
    print("="*60)
    
    if not (os.path.exists('floorplan.geojson') and os.path.exists('paths.json')):
        print("! Skipping - sample files not available")
        print("  Create floorplan.geojson and paths.json first")
        return
    
    try:
        from path_visualizer import IsovistPathVisualizer
        
        print("Testing visualizer initialization...")
        visualizer = IsovistPathVisualizer('floorplan.geojson', 'paths.json')
        print("✓ Visualizer initialized successfully")
        
        print("\nTest passed! You can now run:")
        print("  python path_visualizer.py floorplan.geojson paths.json")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all checks"""
    print("\n" + "#"*60)
    print("# Isovist Path Visualizer - Setup Verification")
    print("#"*60)
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_visibility_module(),
        check_sample_files(),
        check_visualizer_script()
    ]
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✓ All {total} checks passed!")
        print("\nYou're ready to generate visualizations!")
        run_sample_test()
    else:
        print(f"✗ {total - passed} of {total} checks failed")
        print("\nPlease fix the issues above before running the visualizer.")
    
    print("\n" + "#"*60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)