"""
IDA* with Dijkstra Fallback for Presentation
This version is specifically for presentation purposes.
If IDA* takes more than 1 minute, it falls back to Dijkstra.
"""

from typing import Optional
from datetime import datetime
import time
import threading

from .ida_star_balanced import gmaps_style_route_balanced_ida_star
from .data_structures import TransportationGraph, Route


def gmaps_style_route_ida_star_with_fallback(
    graph: TransportationGraph,
    origin_name: str,
    origin_coords: tuple,
    dest_name: str,
    dest_coords: tuple,
    optimization_mode: str = "time",
    departure_time: datetime = None,
    timeout_seconds: float = 60.0  # 1 minute timeout for fallback
):
    """
    IDA* routing with Dijkstra fallback for presentation.
    
    Returns:
        tuple: (route, metadata) where metadata contains:
            - 'algorithm_used': 'ida_star' or 'dijkstra'
            - 'fallback_used': bool
            - 'search_time_seconds': float
            - 'timeout_reached': bool
    """
    if departure_time is None:
        departure_time = datetime.now()
    
    # Import Dijkstra for fallback
    import sys
    import os
    
    # Add paths for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    src_dir = os.path.join(project_root, 'src')
    sys.path.insert(0, project_root)
    sys.path.insert(0, src_dir)
    
    from core.gmaps_style_routing import gmaps_style_route as dijkstra_route
    
    metadata = {
        'algorithm_used': 'ida_star',
        'fallback_used': False,
        'search_time_seconds': 0.0,
        'timeout_reached': False
    }
    
    start_time = time.time()
    
    try:
        # Try IDA* with timeout
        print(f"\n{'='*90}")
        print(f"🎯 IDA* SEARCH (with {timeout_seconds}s timeout)")
        print(f"{'='*90}")
        
        # Modify the BalancedIDAStarRouter to use our timeout
        # We'll call it directly but with a timeout wrapper
        ida_star_route = None
        
        # Use threading to implement timeout (simplified approach)
        result_container = {'route': None, 'exception': None, 'completed': False}
        
        def search_ida_star():
            try:
                result_container['route'] = gmaps_style_route_balanced_ida_star(
                    graph=graph,
                    origin_name=origin_name,
                    origin_coords=origin_coords,
                    dest_name=dest_name,
                    dest_coords=dest_coords,
                    optimization_mode=optimization_mode,
                    departure_time=departure_time
                )
                result_container['completed'] = True
            except Exception as e:
                result_container['exception'] = e
                result_container['completed'] = True
        
        search_thread = threading.Thread(target=search_ida_star, daemon=True)
        search_thread.start()
        search_thread.join(timeout=timeout_seconds)
        
        elapsed_time = time.time() - start_time
        metadata['search_time_seconds'] = elapsed_time
        
        # Check if thread is still running (timeout occurred)
        if search_thread.is_alive():
            # Timeout reached - fallback to Dijkstra
            metadata['timeout_reached'] = True
            metadata['algorithm_used'] = 'dijkstra'
            metadata['fallback_used'] = True
            print(f"\n⏱️  IDA* timeout after {elapsed_time:.2f}s, falling back to Dijkstra...")
            
            # Fallback to Dijkstra
            ida_star_route = dijkstra_route(
                graph=graph,
                origin_name=origin_name,
                origin_coords=origin_coords,
                dest_name=dest_name,
                dest_coords=dest_coords,
                optimization_mode=optimization_mode,
                departure_time=departure_time
            )
            
            if ida_star_route:
                print(f"✅ Dijkstra fallback found route")
            else:
                print(f"❌ Dijkstra fallback found no route")
        else:
            # IDA* completed
            if result_container['exception']:
                raise result_container['exception']
            
            if result_container['route']:
                print(f"✅ IDA* found route in {elapsed_time:.2f}s")
                metadata['algorithm_used'] = 'ida_star'
                metadata['fallback_used'] = False
                ida_star_route = result_container['route']
            else:
                # No route found, try Dijkstra fallback
                metadata['fallback_used'] = True
                metadata['algorithm_used'] = 'dijkstra'
                print(f"\n⚠️  IDA* found no route after {elapsed_time:.2f}s, falling back to Dijkstra...")
                
                ida_star_route = dijkstra_route(
                    graph=graph,
                    origin_name=origin_name,
                    origin_coords=origin_coords,
                    dest_name=dest_name,
                    dest_coords=dest_coords,
                    optimization_mode=optimization_mode,
                    departure_time=departure_time
                )
                
                if ida_star_route:
                    print(f"✅ Dijkstra fallback found route")
                else:
                    print(f"❌ Dijkstra fallback found no route")
        
        return ida_star_route, metadata
        
    except Exception as e:
        # If IDA* fails completely, fallback to Dijkstra
        elapsed_time = time.time() - start_time
        metadata['search_time_seconds'] = elapsed_time
        metadata['fallback_used'] = True
        metadata['algorithm_used'] = 'dijkstra'
        
        print(f"\n⚠️  IDA* error: {e}, falling back to Dijkstra...")
        
        try:
            fallback_route = dijkstra_route(
                graph=graph,
                origin_name=origin_name,
                origin_coords=origin_coords,
                dest_name=dest_name,
                dest_coords=dest_coords,
                optimization_mode=optimization_mode,
                departure_time=departure_time
            )
            
            if fallback_route:
                print(f"✅ Dijkstra fallback found route")
            else:
                print(f"❌ Dijkstra fallback found no route")
            
            return fallback_route, metadata
        except Exception as fallback_error:
            print(f"❌ Dijkstra fallback also failed: {fallback_error}")
            return None, metadata

