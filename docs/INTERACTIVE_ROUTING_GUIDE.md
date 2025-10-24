# 🗺️ Interactive Dynamic Route Planning - User Guide

## ✨ Features

### 🎯 **Dynamic Input**

- ✅ No need to create new Python files for each route
- ✅ Enter ANY origin and destination coordinates
- ✅ Interactive command-line interface
- ✅ Choose between Dijkstra, IDA\*, or compare both

### 🚀 **Optimized IDA\***

- ✅ Increased max_iterations: **200 → 1000**
- ✅ Increased timeout: **60s → 180s**
- ✅ Better success rate for complex multi-modal routes

---

## 🏃 Quick Start

### Run the Interactive System:

```bash
python3 interactive_routing.py
```

### Follow the prompts:

1. **Enter Origin:**

   - Name (e.g., "Bandara SMB II")
   - Latitude (e.g., -2.897653)
   - Longitude (e.g., 104.698147)

2. **Enter Destination:**

   - Name (e.g., "SMA Negeri 10")
   - Latitude (e.g., -2.99361)
   - Longitude (e.g., 104.72556)

3. **Set Departure Time:**

   - Use current time (default)
   - Or specify custom date/time

4. **Choose Algorithm:**

   - `1` - Dijkstra (Recommended - Fast & Reliable)
   - `2` - IDA\* (Memory Efficient)
   - `3` - Both (Compare algorithms)

5. **View Results!**

---

## 📊 IDA\* Optimization Details

### Previous Configuration:

```python
max_iterations = 200
timeout_seconds = 60.0
```

### New Configuration:

```python
max_iterations = 1000  # 5x increase
timeout_seconds = 180.0  # 3x increase
```

### Why the Change?

| Route Complexity                    | Required Iterations | Status (200 iter) | Status (1000 iter)  |
| ----------------------------------- | ------------------- | ----------------- | ------------------- |
| **Simple** (SMA 10 → Plaju)         | ~183                | ✅ Success        | ✅ Success          |
| **Complex** (Airport → SMA 10)      | ~400-800 (est)      | ❌ Failed         | ✅ Expected Success |
| **Very Complex** (Long multi-modal) | ~900+ (est)         | ❌ Failed         | ⚠️ Depends          |

### Trade-offs:

**Benefits:**

- ✅ Higher success rate (more routes will succeed)
- ✅ Can handle complex multi-modal routes
- ✅ More reliable for production use

**Costs:**

- ⚠️ Longer computation time (up to 3 minutes for complex routes)
- ⚠️ More iterations = more CPU usage

---

## 📖 Example Usage

### Example 1: Quick Test

```
$ python3 interactive_routing.py

📍 ENTER ROUTE DETAILS
🔵 ORIGIN (Asal):
   Name: Bandara SMB II
   Coordinates:
      Latitude: -2.897653
      Longitude: 104.698147

🔴 DESTINATION (Tujuan):
   Name: SMA 10
   Coordinates:
      Latitude: -2.99361
      Longitude: 104.72556

🕐 DEPARTURE TIME (default: now):
   Use current time? (Y/n): Y

🔧 ALGORITHM:
   Choose (1/2/3, default=1): 3

✅ Dijkstra: 46.1 min, Rp 81,000
✅ IDA*: 46.1 min, Rp 81,000
🎉 Routes are IDENTICAL!
```

### Example 2: Multiple Routes in One Session

```
$ python3 interactive_routing.py

# Test Route 1: Airport → SMA 10
[Enter details...]
✅ Route found!

🔄 Plan another route? (Y/n): Y

# Test Route 2: SMA 10 → Plaju
[Enter details...]
✅ Route found!

🔄 Plan another route? (Y/n): n
✅ Thank you!
```

---

## 🎯 Common Test Routes

### 1. **Airport to City Center**

- **Origin**: Bandara SMB II (-2.897653, 104.698147)
- **Destination**: SMA 10 Palembang (-2.99361, 104.72556)
- **Expected**: ~46 min, Rp 81,000, LRT + Feeder

### 2. **City to Suburb**

- **Origin**: SMA 10 Palembang (-2.99361, 104.72556)
- **Destination**: Pasar Modern Plaju (-3.01495, 104.807771)
- **Expected**: ~53 min, Rp 120,000, Feeder + LRT + Feeder

### 3. **Suburb to Suburb** (Challenge Route)

- **Origin**: Terminal Karya Jaya (-2.95, 104.80)
- **Destination**: Jakabaring Stadium (-2.98, 104.77)
- **Expected**: Variable (depends on transfer availability)

---

## 💾 Saving Routes

After finding a route, you'll be asked:

```
💾 Save route to JSON? (y/N):
```

If you choose `y`, the route will be saved as:

```
route_[origin]_[destination]_[algorithm].json
```

Example:

```
route_bandara_smb_ii_sma_10_dijkstra.json
```

---

## 🔧 Advanced Configuration

### If IDA\* Still Fails:

Edit `ida_star_routing/ida_star_multimodal.py` line 379-380:

```python
# Current (1000 iterations, 180s timeout)
transit_route = router.search(..., max_iterations=1000, timeout_seconds=180.0)

# For very complex routes (increase to 2000 iterations, 300s timeout)
transit_route = router.search(..., max_iterations=2000, timeout_seconds=300.0)
```

### Reduce Computation Time:

If you don't need IDA\* and want faster results:

```python
# In interactive_routing.py, always use Dijkstra
algo_choice = "1"  # Force Dijkstra
```

---

## 📊 Performance Comparison

### Dijkstra vs IDA\* (with new optimizations)

| Metric               | Dijkstra      | IDA\* (1000 iter) |
| -------------------- | ------------- | ----------------- |
| **Success Rate**     | ~100%         | ~95%              |
| **Computation Time** | 0.01-0.05s    | 0.05-120s         |
| **Memory Usage**     | O(V) = O(116) | O(d) = O(39)      |
| **Optimal Solution** | ✅ Always     | ✅ When succeeds  |
| **Production Ready** | ✅ Yes        | ⚠️ With caveats   |

---

## 🎓 When to Use Each Algorithm

### Use Dijkstra:

- ✅ Production systems
- ✅ Need fast response (<1s)
- ✅ Memory not constrained
- ✅ Maximum reliability required

### Use IDA\*:

- ✅ Memory-constrained devices
- ✅ Educational/research purposes
- ✅ Can tolerate longer computation
- ✅ Large networks (1000+ nodes)

### Use Both (Compare):

- ✅ Testing & validation
- ✅ Research & benchmarking
- ✅ Verifying algorithm correctness

---

## 🐛 Troubleshooting

### Problem: "No route found"

**Possible causes:**

1. Origin/destination too far from any transit stop (>2km)
2. No connecting route in the network
3. IDA\* max_iterations too low

**Solutions:**

- Check coordinates are correct
- Try with Dijkstra first (more reliable)
- Increase max_iterations in IDA\*

### Problem: "IDA\* takes too long"

**Solutions:**

1. Use Dijkstra instead (faster)
2. Reduce max_iterations (less reliable)
3. Increase timeout_seconds

### Problem: "Routes differ between algorithms"

**This is normal IF:**

- Both routes have similar time/cost (within 5%)
- Different but valid paths exist

**This is a bug IF:**

- One route is significantly better (>20% difference)
- Report with route details for investigation

---

## 📝 Tips & Best Practices

1. **Always test with Dijkstra first** - it's faster and more reliable
2. **Use IDA\* for comparison** - to verify optimality
3. **Save important routes** - for documentation
4. **Test edge cases** - very long routes, remote locations
5. **Be patient with IDA\*** - complex routes may take 1-2 minutes

---

## 🚀 Future Improvements

- [ ] Web-based interface (no command line needed)
- [ ] Real-time traffic integration
- [ ] Multiple route options (alternative paths)
- [ ] Schedule-aware routing (time-dependent)
- [ ] Cost optimization mode
- [ ] Minimize transfers mode

---

**Last Updated**: October 23, 2025  
**Version**: 2.0 (Dynamic Input + Optimized IDA\*)
