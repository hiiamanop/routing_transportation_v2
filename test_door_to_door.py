"""
Test Door-to-Door Routing (Google Maps Style)
Example: SMA Negeri 10 Palembang → Pasar Modern Plaju
"""

from datetime import datetime
from ida_star_routing.data_loader import load_network_data
from ida_star_routing.door_to_door import plan_journey, DoorToDoorRouter, Location
from ida_star_routing.main import export_route_to_json


def test_example_user():
    """Test dengan contoh user: SMA Negeri 10 → Pasar Modern Plaju"""
    
    print(f"\n{'='*80}")
    print(f"{'🗺️  DOOR-TO-DOOR ROUTING TEST - GOOGLE MAPS STYLE':^80}")
    print(f"{'='*80}")
    
    # Load network
    print(f"\n📂 Loading transportation network...")
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Example dari user
    print(f"\n📝 TEST CASE: User's Example")
    print(f"="*80)
    
    route = plan_journey(
        graph=graph,
        origin_name="SMA Negeri 10 Palembang",
        origin_coords=(-2.99361, 104.72556),  # Lat, Lon
        origin_address="Jl. Srijaya Negara No. 195, Bukit Lama, Kec. Ilir Bar. I, Kota Palembang",
        dest_name="Pasar Modern Plaju",
        dest_coords=(-3.01495, 104.807771),
        dest_address="2R28+VV3, Plaju Ilir, Plaju, Palembang City, South Sumatra 30119",
        optimization_mode="time",
        departure_time=datetime(2025, 6, 15, 7, 30, 0)  # Keberangkatan jam 7:30 pagi
    )
    
    if route:
        # Export hasil
        export_route_to_json(route, "door_to_door_example.json")
        
        return route
    else:
        print(f"\n❌ No route found")
        return None


def test_multiple_examples():
    """Test multiple door-to-door scenarios"""
    
    graph = load_network_data("dataset/network_data_complete.json")
    
    test_cases = [
        {
            'name': 'Test 1: Bandara → Palembang Icon Mall',
            'origin_name': 'Bandara SMB II',
            'origin_coords': (-2.894114, 104.705661),
            'dest_name': 'Palembang Icon Mall',
            'dest_coords': (-2.987654, 104.756789),
        },
        {
            'name': 'Test 2: Universitas Sriwijaya → Jakabaring',
            'origin_name': 'Universitas Sriwijaya (Indralaya)',
            'origin_coords': (-3.021234, 104.651234),
            'dest_name': 'Jakabaring Sport City',
            'dest_coords': (-3.012345, 104.789012),
        },
        {
            'name': 'Test 3: Rumah Sakit → Pasar 16 Ilir',
            'origin_name': 'RSMH Palembang',
            'origin_coords': (-2.982456, 104.761234),
            'dest_name': 'Pasar 16 Ilir',
            'dest_coords': (-2.988765, 104.771234),
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"{test['name']:^80}")
        print(f"{'='*80}")
        
        route = plan_journey(
            graph=graph,
            origin_name=test['origin_name'],
            origin_coords=test['origin_coords'],
            dest_name=test['dest_name'],
            dest_coords=test['dest_coords'],
            optimization_mode="time"
        )
        
        results.append({
            'test': test['name'],
            'route': route,
            'success': route is not None
        })
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    for result in results:
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        print(f"{status} - {result['test']}")
        if result['route']:
            print(f"         Time: {result['route'].total_time_minutes:.0f} min, "
                  f"Cost: Rp {result['route'].total_cost:,}, "
                  f"Distance: {result['route'].total_distance_km:.2f} km")
    
    return results


def test_optimization_modes():
    """Test different optimization modes for door-to-door routing"""
    
    print(f"\n{'='*80}")
    print(f"🎯 TESTING DIFFERENT OPTIMIZATION MODES")
    print(f"{'='*80}")
    
    graph = load_network_data("dataset/network_data_complete.json")
    
    # Same origin and destination, different optimization
    origin_name = "SMA Negeri 10 Palembang"
    origin_coords = (-2.99361, 104.72556)
    dest_name = "Pasar Modern Plaju"
    dest_coords = (-3.01495, 104.807771)
    
    modes = ["time", "cost", "transfers", "balanced"]
    results = {}
    
    for mode in modes:
        print(f"\n{'─'*80}")
        print(f"🔧 Optimization Mode: {mode.upper()}")
        print(f"{'─'*80}")
        
        origin = Location(origin_name, origin_coords[0], origin_coords[1])
        destination = Location(dest_name, dest_coords[0], dest_coords[1])
        
        router = DoorToDoorRouter(graph, mode)
        route = router.route(origin, destination)
        
        if route:
            results[mode] = {
                'time': route.total_time_minutes,
                'cost': route.total_cost,
                'distance': route.total_distance_km,
                'segments': len(route.segments),
                'score': route.optimization_score
            }
    
    # Comparison table
    print(f"\n{'='*80}")
    print(f"📊 OPTIMIZATION MODE COMPARISON")
    print(f"{'='*80}")
    print(f"\n{'Mode':<15} {'Time (min)':<12} {'Cost (Rp)':<12} {'Distance (km)':<15} {'Segments':<10}")
    print(f"{'─'*80}")
    
    for mode, data in results.items():
        print(f"{mode.capitalize():<15} "
              f"{data['time']:<12.1f} "
              f"{data['cost']:<12,} "
              f"{data['distance']:<15.2f} "
              f"{data['segments']:<10}")
    
    return results


def demo_interactive():
    """Interactive demo for door-to-door routing"""
    
    print(f"\n{'='*80}")
    print(f"{'🚀 DOOR-TO-DOOR ROUTING - INTERACTIVE DEMO':^80}")
    print(f"{'='*80}")
    
    graph = load_network_data("dataset/network_data_complete.json")
    
    print(f"\n📝 Enter journey details:")
    print(f"   (Press Enter to use default example)")
    
    # Origin
    origin_name = input(f"\n📍 Origin name [SMA Negeri 10 Palembang]: ").strip()
    if not origin_name:
        origin_name = "SMA Negeri 10 Palembang"
        origin_lat = -2.99361
        origin_lon = 104.72556
    else:
        try:
            origin_lat = float(input(f"   Latitude: "))
            origin_lon = float(input(f"   Longitude: "))
        except:
            print(f"   Using default coordinates")
            origin_lat = -2.99361
            origin_lon = 104.72556
    
    # Destination
    dest_name = input(f"\n📍 Destination name [Pasar Modern Plaju]: ").strip()
    if not dest_name:
        dest_name = "Pasar Modern Plaju"
        dest_lat = -3.01495
        dest_lon = 104.807771
    else:
        try:
            dest_lat = float(input(f"   Latitude: "))
            dest_lon = float(input(f"   Longitude: "))
        except:
            print(f"   Using default coordinates")
            dest_lat = -3.01495
            dest_lon = 104.807771
    
    # Optimization mode
    print(f"\n⚙️  Optimization mode:")
    print(f"   1. Time (fastest)")
    print(f"   2. Cost (cheapest)")
    print(f"   3. Transfers (minimum)")
    print(f"   4. Balanced")
    
    mode_choice = input(f"\n   Select (1-4) [1]: ").strip() or "1"
    mode_map = {'1': 'time', '2': 'cost', '3': 'transfers', '4': 'balanced'}
    optimization_mode = mode_map.get(mode_choice, 'time')
    
    # Plan journey
    route = plan_journey(
        graph=graph,
        origin_name=origin_name,
        origin_coords=(origin_lat, origin_lon),
        dest_name=dest_name,
        dest_coords=(dest_lat, dest_lon),
        optimization_mode=optimization_mode
    )
    
    if route:
        # Ask to export
        export_choice = input(f"\n💾 Export to JSON? (y/n): ").strip().lower()
        if export_choice == 'y':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"door_to_door_{timestamp}.json"
            export_route_to_json(route, filename)
    
    return route


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "example":
            # Test user's example
            test_example_user()
        
        elif command == "multiple":
            # Test multiple scenarios
            test_multiple_examples()
        
        elif command == "modes":
            # Test different optimization modes
            test_optimization_modes()
        
        elif command == "interactive":
            # Interactive mode
            demo_interactive()
        
        else:
            print(f"Unknown command: {command}")
            print(f"\nUsage:")
            print(f"  python test_door_to_door.py example     - Test user's example")
            print(f"  python test_door_to_door.py multiple    - Test multiple scenarios")
            print(f"  python test_door_to_door.py modes       - Compare optimization modes")
            print(f"  python test_door_to_door.py interactive - Interactive demo")
    
    else:
        # Default: Run user's example
        print(f"\n🚀 Running default test (user's example)...")
        print(f"   Use 'python test_door_to_door.py --help' for more options")
        
        test_example_user()

