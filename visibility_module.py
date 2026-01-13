import sys
import os

class VisibilityModule:
    """Python wrapper for visibility polygon C++ library"""
    
    def __init__(self):
        self.module = None
        self._load_module()
    
    def _load_module(self):
        """Load the pybind11 compiled module"""
        try:
            # Add current directory to path if not already there
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            # Python will automatically find visibility_polygon.cpython-311-darwin.so
            # when we import visibility_polygon
            import visibility_polygon
            self.module = visibility_polygon
            print("✓ Visibility polygon module loaded successfully")
            
        except ImportError as e:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"✗ Failed to import visibility_polygon module: {e}")
            print(f"  Current directory: {current_dir}")
            print(f"  Looking for: visibility_polygon.cpython-*.so or visibility_polygon.so")
            
            # List .so files in directory for debugging
            so_files = [f for f in os.listdir(current_dir) if f.endswith('.so')]
            if so_files:
                print(f"  Found .so files: {so_files}")
            else:
                print(f"  No .so files found in {current_dir}")
            
            raise RuntimeError(f"Failed to load visibility_polygon module: {e}")
    
    def compute_visibility_polygon(
        self,
        viewpoint: tuple,
        obstacles: list,
        screen_width: int,
        screen_height: int,
        ray_length: float = 3000.0
    ) -> list:
        """
        Compute visibility polygon from viewpoint with given obstacles
        
        Args:
            viewpoint: (x, y) tuple for viewpoint position
            obstacles: List of polygons, each polygon is a list of (x, y) points
            screen_width: Canvas width
            screen_height: Canvas height
            ray_length: Maximum ray distance
            
        Returns:
            List of (x, y) points forming the visibility polygon
        """
        if self.module is None:
            raise RuntimeError("Visibility module not loaded")
        
        try:
            # Create Point for viewpoint
            pov = self.module.Point(float(viewpoint[0]), float(viewpoint[1]))
            
            # Create obstacle polygons
            obstacle_list = []
            for obstacle_points in obstacles:
                poly = self.module.Polygon2()
                for point in obstacle_points:
                    x, y = float(point[0]), float(point[1])
                    poly.add_vertex(x, y)
                obstacle_list.append(poly)
            
            print(f"Computing visibility from ({viewpoint[0]:.1f}, {viewpoint[1]:.1f}) with {len(obstacle_list)} obstacles")
            
            # Compute visibility polygon
            result = self.module.compute_visibility_polygon(
                pov,
                obstacle_list,
                int(screen_width),
                int(screen_height),
                float(ray_length)
            )
            
            # Convert result to list of tuples
            points = [(point.x, point.y) for point in result]
            print(f"✓ Computed visibility polygon with {len(points)} points")
            
            return points
            
        except AttributeError as e:
            raise RuntimeError(f"Module function not found: {e}. Available functions: {dir(self.module)}")
        except Exception as e:
            import traceback
            print(f"Error computing visibility: {traceback.format_exc()}")
            raise RuntimeError(f"Error computing visibility polygon: {e}")

# Create singleton instance
_visibility_module = None

def get_visibility_module():
    """Get or create visibility module singleton"""
    global _visibility_module
    if _visibility_module is None:
        _visibility_module = VisibilityModule()
    return _visibility_module
