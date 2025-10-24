"""
Comprehensive Testing of IDA* Multi-Modal Route Planning System
Demonstrates all features and optimization modes
"""

from ida_star_routing.data_loader import load_network_data
from ida_star_routing.ida_star import IDAStarRouter
from ida_star_routing.main import print_route_summary, export_route_to_json
from datetime import datetime
import json


def test_all_optimization_modes():
    """Test all optimization modes (time, cost, transfers, balanced)"""
    
    print("\n" + "="*80)
    print("🚀 COMPREHENSIVE IDA* ROUTING SYSTEM TEST")
    print("="*80)
    
    # Load network
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Find LRT stops for testing
    lrt_stops = sorted([s for s in graph.stops.values() if s.mode.value == "LRT"], 
                       key=lambda s: s.id)
    
    start = lrt_stops[0]  # Bandara SMB 2
    goal = lrt_stops[5]   # Demang
    
    print(f"\n🎯 TEST ROUTE:")
    print(f"   From: {start.name}")
    print(f"   To:   {goal.name}")
    
    modes = ["time", "cost", "transfers", "balanced"]
    results = {}
    
    for mode in modes:
        print(f"\n" + "="*80)
        print(f"🧪 TEST: Optimization Mode = {mode.upper()}")
        print(f"="*80)
        
        router = IDAStarRouter(graph, mode)
        route = router.search(start, goal, departure_time=datetime(2025, 6, 15, 7, 0, 0))
        
        if route:
            print_route_summary(route)
            results[mode] = route
            
            # Export to JSON
            export_route_to_json(route, f"test_route_{mode}.json")
        else:
            print(f"❌ No route found for mode: {mode}")
    
    # Comparison
    print(f"\n" + "="*80)
    print(f"📊 COMPARISON OF OPTIMIZATION MODES")
    print(f"="*80)
    
    print(f"\n{'Mode':<15} {'Time (min)':<12} {'Cost (IDR)':<12} {'Distance (km)':<15} {'Transfers':<10}")
    print(f"-"*80)
    
    for mode, route in results.items():
        print(f"{mode:<15} {route.total_time_minutes:<12.2f} {route.total_cost:<12,} "
              f"{route.total_distance_km:<15.2f} {route.num_transfers:<10}")
    
    return results


def test_different_distances():
    """Test routes of different distances"""
    
    print(f"\n" + "="*80)
    print(f"🧪 TEST: Different Route Distances")
    print(f"="*80)
    
    graph = load_network_data("dataset/network_data_complete.json")
    lrt_stops = sorted([s for s in graph.stops.values() if s.mode.value == "LRT"], 
                       key=lambda s: s.id)
    
    test_cases = [
        ("Short", lrt_stops[0], lrt_stops[2]),   # Bandara → Punti Kayu
        ("Medium", lrt_stops[0], lrt_stops[5]),  # Bandara → Demang
        ("Long", lrt_stops[0], lrt_stops[11]),   # Bandara → Jakabaring
    ]
    
    router = IDAStarRouter(graph, "time")
    
    for label, start, goal in test_cases:
        print(f"\n📍 {label} Distance Test:")
        print(f"   {start.name} → {goal.name}")
        
        route = router.search(start, goal)
        
        if route:
            print(f"   ✅ Found: {route.total_time_minutes:.1f} min, "
                  f"Rp {route.total_cost:,}, {route.total_distance_km:.2f} km, "
                  f"{len(route.segments)} segments")
        else:
            print(f"   ❌ Not found")


def test_feeder_routes():
    """Test feeder angkot routes"""
    
    print(f"\n" + "="*80)
    print(f"🧪 TEST: Feeder Angkot Routes")
    print(f"="*80)
    
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Get feeder stops by route
    feeder_routes = {}
    for stop in graph.stops.values():
        if 'Feeder' in stop.route and stop.route not in feeder_routes:
            feeder_routes[stop.route] = []
        if 'Feeder' in stop.route:
            feeder_routes[stop.route].append(stop)
    
    # Test first available feeder route
    for route_name, stops in feeder_routes.items():
        if len(stops) >= 3:
            stops_sorted = sorted(stops, key=lambda s: s.id)
            start = stops_sorted[0]
            goal = stops_sorted[-1]
            
            print(f"\n📍 Route: {route_name}")
            print(f"   {start.name} → {goal.name}")
            
            router = IDAStarRouter(graph, "time")
            route = router.search(start, goal)
            
            if route:
                print(f"   ✅ Found: {route.total_time_minutes:.1f} min, "
                      f"Rp {route.total_cost:,}, {route.total_distance_km:.2f} km")
                print(f"   Segments: {len(route.segments)}")
                
                # Show first few segments
                print(f"   Path:")
                for seg in route.segments[:3]:
                    print(f"      {seg.sequence}. {seg.from_stop.name} → {seg.to_stop.name} ({seg.duration_minutes:.1f} min)")
                if len(route.segments) > 3:
                    print(f"      ... ({len(route.segments)-3} more segments)")
            else:
                print(f"   ❌ Not found")
            
            break  # Test only first route


def generate_summary_report():
    """Generate comprehensive summary report"""
    
    print(f"\n" + "="*80)
    print(f"📊 GENERATING SUMMARY REPORT")
    print(f"="*80)
    
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Run comprehensive tests
    results = test_all_optimization_modes()
    
    # Create summary JSON
    summary = {
        "test_date": datetime.now().isoformat(),
        "network_stats": {
            "total_stops": len(graph.stops),
            "total_edges": sum(len(e) for e in graph.edges.values()),
            "lrt_stops": sum(1 for s in graph.stops.values() if s.mode.value == "LRT"),
            "feeder_stops": sum(1 for s in graph.stops.values() if s.mode.value == "FEEDER_ANGKOT"),
            "teman_bus_stops": sum(1 for s in graph.stops.values() if s.mode.value == "TEMAN_BUS")
        },
        "test_results": {
            mode: {
                "time_minutes": route.total_time_minutes,
                "cost_idr": route.total_cost,
                "distance_km": route.total_distance_km,
                "segments": len(route.segments),
                "transfers": route.num_transfers,
                "optimization_score": route.optimization_score
            }
            for mode, route in results.items()
        },
        "algorithm_stats": {
            "algorithm": "IDA* (Iterative Deepening A*)",
            "characteristics": [
                "Memory efficient (DFS-like)",
                "Optimal path finding",
                "Admissible heuristics",
                "Iterative deepening with cost bounds"
            ]
        }
    }
    
    # Export summary
    with open("ida_star_test_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Summary report exported: ida_star_test_summary.json")
    
    return summary


if __name__ == "__main__":
    print(f"\n{'='*80}")
    print(f"{'IDA* MULTI-MODAL ROUTING SYSTEM - COMPREHENSIVE TEST':^80}")
    print(f"{'='*80}")
    print(f"{'Palembang Public Transportation Network':^80}")
    print(f"{'='*80}")
    
    try:
        # Run all tests
        test_all_optimization_modes()
        test_different_distances()
        test_feeder_routes()
        generate_summary_report()
        
        print(f"\n" + "="*80)
        print(f"✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print(f"="*80)
        
        print(f"\n📁 Generated Files:")
        print(f"   - test_route_time.json")
        print(f"   - test_route_cost.json")
        print(f"   - test_route_transfers.json")
        print(f"   - test_route_balanced.json")
        print(f"   - ida_star_test_summary.json")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

