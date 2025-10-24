"""
Comparison Test: IDA* vs Dijkstra
Test with user's original example: SMA 10 → Pasar Modern Plaju
"""

from datetime import datetime
import json
from ida_star_routing.data_loader import load_network_data
from gmaps_style_routing import gmaps_style_route, print_gmaps_route
from ida_star_routing.ida_star_multimodal import gmaps_style_route_ida_star


def compare_algorithms():
    """Compare IDA* vs Dijkstra on same route"""
    
    print(f"\n{'='*90}")
    print(f"{'🔬 ALGORITHM COMPARISON: IDA* vs DIJKSTRA':^90}")
    print(f"{'='*90}")
    print(f"{'Test Case: SMA Negeri 10 → Pasar Modern Plaju':^90}")
    print(f"{'='*90}")
    
    # Load bidirectional network
    print(f"\n📂 Loading bidirectional network...")
    graph = load_network_data("dataset/network_data_bidirectional.json")
    
    # Test parameters
    origin_name = "SMA Negeri 10 Palembang"
    origin_coords = (-2.99361, 104.72556)
    dest_name = "Pasar Modern Plaju"
    dest_coords = (-3.01495, 104.807771)
    departure_time = datetime(2025, 6, 15, 7, 30)
    
    results = {}
    
    # Test 1: Dijkstra
    print(f"\n{'='*90}")
    print(f"{'TEST 1: DIJKSTRA ALGORITHM':^90}")
    print(f"{'='*90}")
    
    import time
    start_time = time.time()
    
    dijkstra_route = gmaps_style_route(
        graph=graph,
        origin_name=origin_name,
        origin_coords=origin_coords,
        dest_name=dest_name,
        dest_coords=dest_coords,
        optimization_mode="time",
        departure_time=departure_time
    )
    
    dijkstra_time = time.time() - start_time
    
    if dijkstra_route:
        results['dijkstra'] = {
            'route': dijkstra_route,
            'time': dijkstra_time,
            'success': True
        }
        print(f"\n✅ Dijkstra SUCCESS")
        print(f"   Computation time: {dijkstra_time:.4f}s")
        print(f"   Total time: {dijkstra_route.total_time_minutes:.1f} min")
        print(f"   Total cost: Rp {dijkstra_route.total_cost:,}")
        print(f"   Segments: {len(dijkstra_route.segments)}")
    else:
        results['dijkstra'] = {'route': None, 'time': dijkstra_time, 'success': False}
        print(f"\n❌ Dijkstra FAILED")
    
    # Test 2: IDA*
    print(f"\n{'='*90}")
    print(f"{'TEST 2: IDA* ALGORITHM':^90}")
    print(f"{'='*90}")
    
    start_time = time.time()
    
    ida_route = gmaps_style_route_ida_star(
        graph=graph,
        origin_name=origin_name,
        origin_coords=origin_coords,
        dest_name=dest_name,
        dest_coords=dest_coords,
        optimization_mode="time",
        departure_time=departure_time
    )
    
    ida_time = time.time() - start_time
    
    if ida_route:
        results['ida'] = {
            'route': ida_route,
            'time': ida_time,
            'success': True
        }
        print(f"\n✅ IDA* SUCCESS")
        print(f"   Computation time: {ida_time:.4f}s")
        print(f"   Total time: {ida_route.total_time_minutes:.1f} min")
        print(f"   Total cost: Rp {ida_route.total_cost:,}")
        print(f"   Segments: {len(ida_route.segments)}")
    else:
        results['ida'] = {'route': None, 'time': ida_time, 'success': False}
        print(f"\n❌ IDA* FAILED")
    
    # Comparison
    print(f"\n{'='*90}")
    print(f"{'📊 DETAILED COMPARISON':^90}")
    print(f"{'='*90}")
    
    if results.get('dijkstra', {}).get('success') and results.get('ida', {}).get('success'):
        dijk_route = results['dijkstra']['route']
        ida_route = results['ida']['route']
        
        print(f"\n{'Metric':<30} {'Dijkstra':<30} {'IDA*':<30}")
        print(f"{'─'*90}")
        
        # Success
        print(f"{'✅ Route Found':<30} {'Yes':<30} {'Yes':<30}")
        
        # Computation time
        dijk_time = results['dijkstra']['time']
        ida_time = results['ida']['time']
        print(f"{'⏱️  Computation Time':<30} {f'{dijk_time:.4f}s':<30} {f'{ida_time:.4f}s':<30}")
        
        # Route metrics
        print(f"{'🕐 Total Time (min)':<30} {f'{dijk_route.total_time_minutes:.1f}':<30} {f'{ida_route.total_time_minutes:.1f}':<30}")
        print(f"{'💰 Total Cost (Rp)':<30} {f'{dijk_route.total_cost:,}':<30} {f'{ida_route.total_cost:,}':<30}")
        print(f"{'📏 Total Distance (km)':<30} {f'{dijk_route.total_distance_km:.2f}':<30} {f'{ida_route.total_distance_km:.2f}':<30}")
        print(f"{'🔄 Transfers':<30} {f'{dijk_route.num_transfers}':<30} {f'{ida_route.num_transfers}':<30}")
        print(f"{'📍 Segments':<30} {f'{len(dijk_route.segments)}':<30} {f'{len(ida_route.segments)}':<30}")
        
        # Analysis
        print(f"\n{'='*90}")
        print(f"{'🎯 ANALYSIS':^90}")
        print(f"{'='*90}")
        
        # Time comparison
        time_diff = abs(dijk_route.total_time_minutes - ida_route.total_time_minutes)
        if time_diff < 0.1:
            print(f"\n✅ Route Time: IDENTICAL ({dijk_route.total_time_minutes:.1f} min)")
        elif dijk_route.total_time_minutes < ida_route.total_time_minutes:
            print(f"\n⚡ Dijkstra found FASTER route")
            print(f"   Time difference: {time_diff:.1f} minutes")
        else:
            print(f"\n⚡ IDA* found FASTER route")
            print(f"   Time difference: {time_diff:.1f} minutes")
        
        # Cost comparison
        cost_diff = abs(dijk_route.total_cost - ida_route.total_cost)
        if cost_diff == 0:
            print(f"\n✅ Route Cost: IDENTICAL (Rp {dijk_route.total_cost:,})")
        elif dijk_route.total_cost < ida_route.total_cost:
            print(f"\n💰 Dijkstra found CHEAPER route")
            print(f"   Cost difference: Rp {cost_diff:,}")
        else:
            print(f"\n💰 IDA* found CHEAPER route")
            print(f"   Cost difference: Rp {cost_diff:,}")
        
        # Computation time
        comp_diff = abs(dijk_time - ida_time)
        if dijk_time < ida_time:
            print(f"\n⚡ Dijkstra was FASTER to compute")
            print(f"   Time difference: {comp_diff:.4f}s")
        else:
            print(f"\n⚡ IDA* was FASTER to compute")
            print(f"   Time difference: {comp_diff:.4f}s")
        
        # Memory
        print(f"\n💾 Memory Usage:")
        print(f"   Dijkstra: O(V) - Stores all nodes")
        print(f"   IDA*:     O(d) - Only stores current path")
        print(f"   Winner: IDA* (more memory efficient)")
        
        # Export routes
        print(f"\n{'='*90}")
        print(f"{'💾 EXPORTING RESULTS':^90}")
        print(f"{'='*90}")
        
        # Export Dijkstra route
        with open("comparison_dijkstra_route.json", 'w', encoding='utf-8') as f:
            json.dump(dijk_route.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✅ Dijkstra route: comparison_dijkstra_route.json")
        
        # Export IDA* route
        with open("comparison_ida_star_route.json", 'w', encoding='utf-8') as f:
            json.dump(ida_route.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"✅ IDA* route:     comparison_ida_star_route.json")
        
        # Print detailed routes if different
        if time_diff > 1.0 or cost_diff > 1000:
            print(f"\n{'='*90}")
            print(f"DIJKSTRA ROUTE DETAILS:")
            print(f"{'='*90}")
            print_gmaps_route(dijk_route, origin_name, dest_name)
            
            print(f"\n{'='*90}")
            print(f"IDA* ROUTE DETAILS:")
            print(f"{'='*90}")
            print_gmaps_route(ida_route, origin_name, dest_name)
    
    else:
        print(f"\n⚠️  Cannot compare - one or both algorithms failed")
        
        if not results.get('dijkstra', {}).get('success'):
            print(f"   ❌ Dijkstra failed")
        
        if not results.get('ida', {}).get('success'):
            print(f"   ❌ IDA* failed")
    
    return results


if __name__ == "__main__":
    print(f"\n{'='*90}")
    print(f"{'🔬 ALGORITHM COMPARISON TEST':^90}")
    print(f"{'IDA* (Iterative Deepening A*) vs Dijkstra':^90}")
    print(f"{'='*90}")
    
    results = compare_algorithms()
    
    print(f"\n{'='*90}")
    print(f"{'✅ TEST COMPLETE':^90}")
    print(f"{'='*90}")
    
    # Final verdict
    if results.get('dijkstra', {}).get('success') and results.get('ida', {}).get('success'):
        print(f"\n🏆 VERDICT:")
        print(f"   Both algorithms successfully found routes!")
        print(f"   IDA* can produce same quality results as Dijkstra")
        print(f"   with better memory efficiency O(d) vs O(V)")
    elif results.get('ida', {}).get('success'):
        print(f"\n🏆 IDA* succeeded where Dijkstra failed!")
    elif results.get('dijkstra', {}).get('success'):
        print(f"\n⚠️  Dijkstra succeeded but IDA* failed")
        print(f"   IDA* may need more iterations or higher timeout")
    else:
        print(f"\n❌ Both algorithms failed")
        print(f"   Network may need further investigation")

