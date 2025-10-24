# 🔬 IDA\* vs Dijkstra: Comprehensive Comparison

## Test Case

**Route**: SMA Negeri 10 Palembang → Pasar Modern Plaju  
**Origin**: -2.99361, 104.72556  
**Destination**: -3.01495, 104.807771  
**Date**: June 15, 2025, 07:30  
**Optimization Mode**: Time

---

## 📊 Results Summary

| Metric                    | Dijkstra              | IDA\*                         | Winner      |
| ------------------------- | --------------------- | ----------------------------- | ----------- |
| **Solution Found**        | ✅ Yes                | ✅ Yes                        | 🤝 Tie      |
| **Route Quality**         | 53 minutes            | 53 minutes                    | 🤝 Tie      |
| **Total Cost**            | Rp 120,000            | Rp 120,000                    | 🤝 Tie      |
| **Transfers**             | 2                     | 2                             | 🤝 Tie      |
| **Segments**              | 40                    | 40                            | 🤝 Tie      |
| **Computation Time**      | ~0.05s                | ~0.05s (after 183 iterations) | 🤝 Tie      |
| **Memory Usage**          | O(V) = O(116)         | O(d) = O(39)                  | ✅ IDA\*    |
| **Max Iterations Needed** | N/A (no limit)        | 183 out of 200                | ⚠️ Dijkstra |
| **Nodes Explored**        | ~116 (all nodes once) | 22,649                        | ⚠️ Dijkstra |

---

## 🛣️ Route Details (Both Algorithms)

### Summary

- **Total Duration**: 53 minutes
- **Total Cost**: Rp 120,000
- **Total Distance**: ~16 km
- **Modes Used**: Walking → LRT → Transfer → Angkot Feeder → Walking
- **Segments**: 40 steps

### Key Segments

1. **Walk to Transit** (4 min)  
   SMA Negeri 10 → Bs stop

2. **LRT Sumsel** (6 segments, ~13 min)

   - SMB Sriwijaya → Asrama Haji
   - Multiple stops along LRT line

3. **Transfer via Walking** (5 min)  
   Asrama Haji LRT → BS stasiun lrt djka B (Feeder Koridor 5)

4. **Angkot Feeder Koridor 5** (31 segments, ~27 min)

   - Long route through Plaju area
   - Multiple stops ending at BS Paud al bayyinah ada

5. **Walk to Destination** (4 min)  
   BS Paud al bayyinah ada → Pasar Modern Plaju

---

## 🔍 Detailed Analysis

### IDA\* Performance Metrics

**First Combination Tested:**

- **Origin Stop**: Bs ada (FEEDER_ANGKOT)
- **Destination Stop**: BS Paud al bayyinah ada (FEEDER_ANGKOT)
- **Initial Bound**: 14.51 minutes
- **Final Bound**: 35.42 minutes (when solution found at iteration 183)
- **Iterations**: 183 out of 200 max
- **Nodes Explored**: 22,649
- **Max Depth**: 39 stops
- **Time**: 0.0500 seconds

**Key Observation**: IDA\* needed 183 iterations to find the optimal solution. With the original limit of 50 iterations, it would have failed.

### Dijkstra Performance Metrics

- **No iteration limit**: Always explores entire reachable network
- **Guaranteed to find**: Optimal solution if one exists
- **Nodes Explored**: ~116 (each node visited at most once)
- **Memory**: Stores all visited nodes and distances
- **Time**: ~0.05 seconds (similar to IDA\*)

---

## ⚖️ Trade-offs

### When IDA\* is Better

✅ **Memory-Constrained Environments**

- Mobile devices
- Embedded systems
- IoT applications
- IDA\* uses O(39) vs Dijkstra's O(116) for this route

✅ **Known Heuristic**

- When you have a good admissible heuristic
- Straight-line distance works well for geographic routing

✅ **Deep but Narrow Search Space**

- Few branches per node
- Solution at moderate depth

### When Dijkstra is Better

✅ **Production Systems**

- Need guaranteed fast results
- Can't risk hitting iteration limit
- Memory not a constraint

✅ **Dense Networks**

- Many connections per node
- IDA\* would explore too many nodes repeatedly

✅ **Multiple Queries**

- Can cache distance matrix
- Amortize computation cost

✅ **Reliability**

- No tuning needed (max_iterations, timeout)
- Always finds solution if exists

---

## 🎯 Critical Finding: Iteration Limit

### Problem

**Original limit**: 50 iterations  
**Required**: 183 iterations  
**Gap**: 266% more iterations needed!

### Impact

- With 50 iterations: IDA\* **FAILS** ❌
- With 200 iterations: IDA\* **SUCCEEDS** ✅

### Recommendation

For multi-modal public transport routing:

- **Minimum**: 200 iterations
- **Recommended**: 500 iterations (safety margin)
- **Timeout**: 60 seconds (prevent infinite loops)

---

## 💡 Key Insights

### 1. Algorithm Optimality

Both IDA\* and Dijkstra found the **exact same route**:

- Same path
- Same duration (53 min)
- Same cost (Rp 120,000)
- Same transfers (2)

This confirms both algorithms are **optimal** when given sufficient resources.

### 2. Computational Complexity

**IDA\* Explored**: 22,649 nodes  
**Dijkstra Explored**: ~116 nodes

Why? IDA\* uses iterative deepening with DFS:

- Explores same nodes multiple times across iterations
- Each iteration goes deeper
- Early iterations explore shallow depths repeatedly

### 3. Memory Efficiency

**IDA\* Memory**: O(39) - only stores current path (max depth 39)  
**Dijkstra Memory**: O(116) - stores all visited nodes

For this small network (116 nodes), memory difference is negligible. But for large networks (10,000+ nodes), IDA\* has significant advantage.

### 4. Heuristic Quality

**Initial Bound**: 14.51 minutes  
**Actual Solution**: 53.3 minutes  
**Heuristic Error**: ~73% underestimate

The heuristic (straight-line distance) is optimistic because:

- Doesn't account for transfers
- Doesn't account for route detours
- Doesn't account for waiting time

Better heuristic could reduce iterations needed.

---

## 🏆 Verdict

### For Palembang Public Transport Network

**Winner: Dijkstra** 🥇

**Reasons:**

1. **Small network** (116 nodes) - memory not an issue
2. **Production reliability** - no tuning needed
3. **Fewer nodes explored** - more efficient
4. **No iteration limit** - guaranteed to find solution

### For Larger Networks (1000+ nodes)

**Winner: IDA\*** 🥇

**Reasons:**

1. **Memory efficient** - critical for large networks
2. **Good heuristics** - can guide search effectively
3. **Scalability** - O(d) memory vs O(V)
4. **Mobile-friendly** - lower memory footprint

---

## 📈 Recommendations

### Current Implementation

**Use Dijkstra** for `gmaps_style_routing.py`:

- Faster (fewer nodes explored)
- More reliable (no iteration limits)
- Simpler code (no iteration tuning)

**Keep IDA\*** as research/alternative:

- Demonstrates memory efficiency
- Educational value
- Useful for future large-scale networks

### Future Improvements

**For IDA\*:**

1. **Improve heuristic**:
   - Account for average transfer time
   - Account for route detours (use road network distance)
   - Learn from historical data
2. **Adaptive iteration limit**:

   - Start with 50, increase if needed
   - Based on network size
   - Based on origin-destination distance

3. **Bidirectional IDA\***:
   - Search from both ends
   - Meet in the middle
   - Significantly reduce iterations

**For Dijkstra:**

1. **Caching**:
   - Cache distance matrix for frequent queries
   - Precompute common routes
2. **Priority queue optimization**:
   - Use Fibonacci heap (O(log n) decrease-key)
   - Currently using Python heapq

---

## 📝 Conclusion

Both **IDA\*** and **Dijkstra** successfully solve the multi-modal routing problem for Palembang's public transport network. They produce **identical optimal routes**.

**Key Takeaway**: Choice depends on constraints:

- **Memory-limited** → IDA\*
- **Time-critical** → Dijkstra
- **General purpose** → Dijkstra

For the current Palembang network (116 nodes), **Dijkstra is recommended** due to its simplicity, reliability, and efficiency.

---

**Last Updated**: October 23, 2025  
**Test Environment**: Python 3.x, Bidirectional Network (222 edges)  
**Test Case**: Real-world route in Palembang, Indonesia
