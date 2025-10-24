"""
Interactive Dynamic Route Planning System
Input koordinat origin & destination secara dinamis
"""

from datetime import datetime
from ida_star_routing.data_loader import load_network_data
from ida_star_routing.ida_star_multimodal import gmaps_style_route_ida_star
from gmaps_style_routing import gmaps_style_route, print_gmaps_route
import json
import sys

def get_float_input(prompt):
    """Get float input with validation"""
    while True:
        try:
            value = float(input(prompt))
            return value
        except ValueError:
            print("❌ Invalid input. Please enter a number.")

def main():
    print("="*100)
    print(" "*30 + "🗺️  INTERACTIVE ROUTE PLANNING")
    print(" "*25 + "Dynamic Multi-Modal Public Transport Routing")
    print("="*100)
    
    # Load network once
    print("\n📂 Loading network...")
    graph = load_network_data("dataset/network_data_bidirectional.json")
    print("✅ Network loaded successfully!")
    print(f"   📊 Complete Network: {len(graph.stops)} stops, {len(graph.edges)} edges")
    print(f"   🚌 Routes: 8 Feeder + 2 Teman Bus + 1 LRT = 11 routes")
    print(f"   🔄 Bidirectional: All routes can be traversed both ways")
    
    while True:
        print("\n" + "="*100)
        print("📍 ENTER ROUTE DETAILS")
        print("="*100)
        
        # Get origin
        print("\n🔵 ORIGIN (Asal):")
        origin_name = input("   Name: ").strip()
        if not origin_name:
            print("❌ Origin name cannot be empty!")
            continue
            
        print("   Coordinates:")
        origin_lat = get_float_input("      Latitude: ")
        origin_lon = get_float_input("      Longitude: ")
        
        # Get destination
        print("\n🔴 DESTINATION (Tujuan):")
        dest_name = input("   Name: ").strip()
        if not dest_name:
            print("❌ Destination name cannot be empty!")
            continue
            
        print("   Coordinates:")
        dest_lat = get_float_input("      Latitude: ")
        dest_lon = get_float_input("      Longitude: ")
        
        # Get departure time (optional)
        print("\n🕐 DEPARTURE TIME (default: now):")
        use_default = input("   Use current time? (Y/n): ").strip().lower()
        
        if use_default in ['n', 'no']:
            year = int(input("      Year (2025): ") or "2025")
            month = int(input("      Month (1-12): "))
            day = int(input("      Day (1-31): "))
            hour = int(input("      Hour (0-23): "))
            minute = int(input("      Minute (0-59): ") or "0")
            departure_time = datetime(year, month, day, hour, minute)
        else:
            departure_time = datetime.now()
        
        # Choose algorithm
        print("\n🔧 ALGORITHM:")
        print("   1. Dijkstra (Recommended - Fast & Reliable)")
        print("   2. IDA* (Memory Efficient - Optimized)")
        print("   3. Both (Compare)")
        
        algo_choice = input("   Choose (1/2/3, default=1): ").strip() or "1"
        
        # Summary
        print("\n" + "="*100)
        print("📋 ROUTE SUMMARY")
        print("="*100)
        print(f"   🔵 From: {origin_name}")
        print(f"      📌 Lat: {origin_lat}, Lon: {origin_lon}")
        print(f"   🔴 To: {dest_name}")
        print(f"      📌 Lat: {dest_lat}, Lon: {dest_lon}")
        print(f"   🕐 Departure: {departure_time}")
        print(f"   🔧 Algorithm: {['Dijkstra', 'IDA*', 'Both'][int(algo_choice)-1]}")
        
        confirm = input("\n   Proceed? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("   ❌ Cancelled.")
            continue
        
        # Run routing
        origin_coords = (origin_lat, origin_lon)
        dest_coords = (dest_lat, dest_lon)
        
        dijkstra_route = None
        ida_route = None
        
        # Run Dijkstra
        if algo_choice in ['1', '3']:
            print("\n" + "="*100)
            print(" "*40 + "🚀 DIJKSTRA ALGORITHM")
            print("="*100)
            
            try:
                dijkstra_route = gmaps_style_route(
                    graph=graph,
                    origin_name=origin_name,
                    origin_coords=origin_coords,
                    dest_name=dest_name,
                    dest_coords=dest_coords,
                    optimization_mode="time",
                    departure_time=departure_time
                )
                
                if dijkstra_route:
                    print(f"\n✅ DIJKSTRA SUCCESS!")
                    print(f"   Duration: {dijkstra_route.total_time_minutes:.1f} min")
                    print(f"   Cost: Rp {dijkstra_route.total_cost:,}")
                    print(f"   Distance: {dijkstra_route.total_distance_km:.2f} km")
                    print(f"   Segments: {len(dijkstra_route.segments)}")
                    
                    # Show detailed route
                    print("\n" + "="*100)
                    print_gmaps_route(dijkstra_route, origin_name, dest_name)
                else:
                    print("\n❌ DIJKSTRA: No route found")
            except Exception as e:
                print(f"\n❌ DIJKSTRA ERROR: {e}")
        
        # Run IDA*
        if algo_choice in ['2', '3']:
            print("\n" + "="*100)
            print(" "*40 + "🧠 IDA* ALGORITHM (OPTIMIZED)")
            print("="*100)
            print("   ✨ Stops immediately after finding first solution")
            print("   ✨ Memory efficient for large networks")
            print("   ✨ Same results as Dijkstra")
            
            try:
                ida_route = gmaps_style_route_ida_star(
                    graph=graph,
                    origin_name=origin_name,
                    origin_coords=origin_coords,
                    dest_name=dest_name,
                    dest_coords=dest_coords,
                    optimization_mode="time",
                    departure_time=departure_time
                )
                
                if ida_route:
                    print(f"\n✅ IDA* SUCCESS!")
                    print(f"   Duration: {ida_route.total_time_minutes:.1f} min")
                    print(f"   Cost: Rp {ida_route.total_cost:,}")
                    print(f"   Distance: {ida_route.total_distance_km:.2f} km")
                    print(f"   Segments: {len(ida_route.segments)}")
                    print(f"   ✨ Optimized: Stops after first solution found")
                    
                    if algo_choice == '2':  # Only show if IDA* alone
                        print("\n" + "="*100)
                        print_gmaps_route(ida_route, origin_name, dest_name)
                else:
                    print("\n❌ IDA*: No route found")
            except Exception as e:
                print(f"\n❌ IDA* ERROR: {e}")
        
        # Compare if both
        if algo_choice == '3' and dijkstra_route and ida_route:
            print("\n" + "="*100)
            print(" "*40 + "📊 COMPARISON")
            print("="*100)
            
            print(f"\n{'Metric':<20} {'Dijkstra':>20} {'IDA*':>20} {'Match?':>12}")
            print("-" * 77)
            
            duration_match = "✅" if abs(dijkstra_route.total_time_minutes - ida_route.total_time_minutes) < 0.1 else "❌"
            print(f"{'Duration':<20} {dijkstra_route.total_time_minutes:>18.1f} min {ida_route.total_time_minutes:>18.1f} min {duration_match:>8}")
            
            cost_match = "✅" if dijkstra_route.total_cost == ida_route.total_cost else "❌"
            print(f"{'Cost':<20} {'Rp ' + f'{dijkstra_route.total_cost:,}':>20} {'Rp ' + f'{ida_route.total_cost:,}':>20} {cost_match:>8}")
            
            segments_match = "✅" if len(dijkstra_route.segments) == len(ida_route.segments) else "❌"
            print(f"{'Segments':<20} {len(dijkstra_route.segments):>20} {len(ida_route.segments):>20} {segments_match:>8}")
            
            all_match = (duration_match == "✅" and cost_match == "✅" and segments_match == "✅")
            print(f"\n{'='*77}")
            if all_match:
                print("🎉 Routes are IDENTICAL!")
            else:
                print("⚠️  Routes differ")
        
        # Save option
        if dijkstra_route or ida_route:
            save = input("\n💾 Save route to JSON? (y/N): ").strip().lower()
            if save in ['y', 'yes']:
                route_to_save = dijkstra_route if dijkstra_route else ida_route
                algo_name = "dijkstra" if dijkstra_route else "ida"
                
                filename = f"route_{origin_name.replace(' ', '_').lower()}_{dest_name.replace(' ', '_').lower()}_{algo_name}.json"
                
                # Convert to dict
                route_dict = {
                    "route_id": route_to_save.route_id,
                    "origin": origin_name,
                    "destination": dest_name,
                    "summary": {
                        "total_time_minutes": route_to_save.total_time_minutes,
                        "total_cost": route_to_save.total_cost,
                        "total_distance_km": route_to_save.total_distance_km,
                        "num_transfers": route_to_save.num_transfers,
                        "departure_time": str(route_to_save.segments[0].departure_time),
                        "arrival_time": str(route_to_save.segments[-1].arrival_time),
                    },
                    "segments": []
                }
                
                for seg in route_to_save.segments:
                    route_dict["segments"].append({
                        "sequence": seg.sequence,
                        "mode": seg.mode.value,
                        "route_name": seg.route_name,
                        "from_stop": seg.from_stop.name,
                        "to_stop": seg.to_stop.name,
                        "duration_minutes": seg.duration_minutes,
                        "cost": seg.cost,
                        "distance_km": seg.distance_km,
                    })
                
                with open(filename, 'w') as f:
                    json.dump(route_dict, f, indent=2)
                
                print(f"   ✅ Saved to: {filename}")
        
        # Continue or exit
        print("\n" + "="*100)
        cont = input("🔄 Plan another route? (Y/n): ").strip().lower()
        if cont in ['n', 'no']:
            print("\n✅ Thank you for using Interactive Route Planning!")
            print("="*100)
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

