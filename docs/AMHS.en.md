# AMHS Concepts & How This Project Maps to Them

*[한국어 버전(Korean)](AMHS.md)*

Written while preparing for an AMHS-track interview at SK hynix. AMHS (Automated Material Handling
System) is the logistics system that moves wafers (in FOUPs) between process tools inside a fab. The
`amhs/` module and `notebooks/07–09` are the result of implementing these concepts directly to build
real understanding, not just reading about them. The dispatching policies here were designed from
scratch rather than lifted from a paper; §8 below is an honest account of where that design overlaps
with — and falls short of — actual published research and industry practice.

## 1. Key Terms

| Term | Description |
|---|---|
| **FOUP** (Front Opening Unified Pod) | A sealed cassette holding 25 wafers. AMHS moves FOUPs, not individual wafers — the FOUP is the unit of transport. |
| **OHT** (Overhead Hoist Transport) | An automated vehicle that runs on an overhead rail and picks up/drops off FOUPs. The de facto standard transport mechanism in 300mm wafer fabs. |
| **Stocker** | An automated buffer that temporarily stores FOUPs. It absorbs throughput mismatches between process tools so the line doesn't stall. When it fills up, congestion downstream propagates upstream (**back-pressure**). |
| **Bay** | A cluster of the same type of process equipment. Transport is split into **intrabay** (within a bay) and **interbay** (between bays). |
| **MCS** (Material Control System) | The "brain" of AMHS. Receives transport requests from the MES (which FOUP, from where, to where) and decides which OHT vehicle handles it. |
| **Dispatching** | The rule/algorithm the MCS uses to assign transport requests to vehicles. Goals: minimize transport time, minimize tool idle time, avoid congestion. |
| **Cycle Time** | Time from a transport request being raised to the FOUP arriving at its destination. The core AMHS KPI. |
| **Vehicle Utilization** | Fraction of total time an OHT vehicle is actually carrying (or moving to carry) a FOUP. Too low means over-invested in vehicles; too high means a bottleneck. |
| **Congestion** | A state where requests/vehicles pile up in a section of the network and wait times spike. Directly shaped by layout design and dispatch quality. |
| **SECS/GEM** | The standard communication protocol between semiconductor equipment and software. MES/MCS/tools exchange transport requests and completions over this protocol. |
| **Hot Lot** | A lot with an urgent deadline or one that needs early confirmation of a suspected issue. Gets priority over normal lots in transport and processing. |

## 2. Why AMHS Matters

- If a wafer can't reach a process tool, the tool sits idle no matter how fast it is — **AMHS effectively sets the ceiling on a fab's overall throughput.**
- If one OHT vehicle fails, that section congests and the congestion propagates to adjacent sections (a domino effect) — which is why **vehicle predictive maintenance** is really line-wide risk management, not just "predict the next breakdown."
- Changing a single dispatching algorithm can materially change throughput with the exact same vehicle fleet, which makes **algorithmic/optimization skill** a comparatively cheap way to move the needle relative to buying more hardware.

## 3. What This Project Covers

| AMHS concept | Implementation in this project |
|---|---|
| Layout (process stations + transport network) | `amhs/layout.py` — reuses the existing 8 process stations from `simulator/` as nodes, adds transport distance/speed |
| Stocker (input buffer) + back-pressure | `amhs/simulation.py` — uses each tool's `simpy.Resource` queue length directly as stocker occupancy; when it's full, the OHT vehicle delays drop-off and waits |
| OHT dispatch simulation + cycle time / utilization / congestion metrics | `amhs/simulation.py` (SimPy discrete-event simulation), `notebooks/07_amhs_dispatch_simulation.ipynb` |
| Dispatch-policy comparison | Same notebook — nearest-vehicle / FCFS / zone-based / predictive-adaptive policies compared on identical scenarios; also runnable live from the dashboard |
| Hot lot priority | `amhs/simulation.py` — the dispatcher picks the next request by hot-lot priority instead of strict FIFO; confirmed the effect only shows up under contention |
| Transport delay / congestion prediction | `notebooks/08_amhs_delay_prediction.ipynb` — XGBoost regression/classification on simulation logs, wired into live dispatching via `amhs/predictive.py` |
| Vehicle predictive maintenance | `amhs/vehicle_health_simulator.py` + `notebooks/09_amhs_predictive_maintenance.ipynb` — the same Isolation Forest + XGBoost ensemble pipeline used on SECOM, reapplied to OHT vehicle sensors (motor current, vibration, temperature), fed back into the simulation via `amhs/maintenance.py` |
| Dashboard integration | `POST /api/amhs/simulate` in `backend/app/main.py` runs the SimPy simulation on demand (< 1s) — the React "AMHS" screen runs dispatch-policy comparison and vehicle-count sensitivity live on button click |

If the SECOM/process-simulator part of this repo covers **FDC (Fault Detection and Classification)** —
"is this wafer defective?" — the AMHS part covers **whether that wafer arrives at the next tool on
time**. Same fab, two different axes (quality vs. logistics), which is why both live in one repository.

## 4. Simulation Results (`notebooks/07_amhs_dispatch_simulation.ipynb`)

> **A bug worth telling the story of**: the first stocker implementation used a separate `simpy.Store`,
> where each FOUP would `put()` into it and then immediately `get()` itself back out. That meant the
> buffer effectively never held anything (it consumed its own contents instantly), so max queue length
> stayed at 1 regardless of load — back-pressure simply wasn't observable. The root cause was treating
> "a FOUP waiting in front of a tool" and "something being pulled out of the stocker" as two separate
> events when they should have been the same thing. Removing the separate stocker and instead using
> **the tool's own `simpy.Resource` queue length as the stocker occupancy signal** (the OHT vehicle
> checks queue length before drop-off and waits if it's full) made queue length actually respond to
> load, vehicle count, and buffer size. Lesson: if a simulation runs cleanly but a core metric is always
> a constant, that's worth being suspicious of, not reassured by.

**Dispatch-policy comparison** (5 vehicles, 10 FOUPs × 1 lap, same seed across policies):

| Policy | Avg cycle time | P95 cycle time | Avg utilization |
|---|---|---|---|
| Nearest vehicle | **91.4s** | 197.8s | 0.047 |
| Zone-based | 115.7s | 270.5s | 0.060 |
| FCFS (ignores position) | 175.1s | 306.9s | 0.089 |
| Predictive (adaptive) | 91.4s | 197.8s | 0.047 |

Position-aware policies (nearest/zone) clearly beat FCFS. The predictive policy chose "nearest" every
single time at this load level, because predicted delay never crossed its congestion threshold — not a
failure, but the policy correctly deciding that adaptive switching isn't needed at low load. This is
consistent with the §5 finding below (the #1 predictor of delay is real-time load): in this scenario,
real-time load itself stays low throughout.

**Vehicle-count sensitivity** (nearest-vehicle policy fixed): 2 vehicles (239s) → 4 (102s) → 6 (76s)
drops steeply, then 6→8 (76→65s) and 8→10 (65→64s) flatten out sharply. **Diminishing returns kick in
around 6–8 vehicles** — beyond that, station processing time itself is the bottleneck, and adding more
vehicles barely moves cycle time.

**Stocker-capacity sensitivity** (4 vehicles fixed): capacity 1 (98.6s) < capacity 2 (102.4s) =
capacity 3 = capacity 5 (102.4s) — **a smaller buffer produces a shorter average transport time.**
A small buffer triggers back-pressure earlier, which naturally caps the amount of WIP in flight at any
given time — and lower WIP means shorter lead time per FOUP, the same relationship lean manufacturing
predicts. Max queue length moves the opposite way (grows with buffer size), which is expected and not
an interesting signal — a bigger buffer just has more room to fill.

**Predictive-maintenance feedback** (§6's model wired directly into the simulation, averaged over 15
seeds — predictive maintenance consumes its own randomness, so a single-seed comparison would be
noisy): 82.3s without predictive maintenance vs. 87.8s with it enabled — **when vehicles periodically
break down and go offline, average cycle time gets about 6.7% worse.** This reproduces, in actual
numbers, the "vehicle failure → congestion domino effect" claim made in §2.

**Hot lot priority**: in the base low-load scenario, hot lots (84.0s) and normal lots (83.4s) are
essentially identical — the pending-request queue almost never has more than one item, so there's
nothing for a priority rule to reorder. Under a deliberately contended scenario (2 vehicles, 20s launch
interval), hot lots average 190.5s vs. 276.5s for normal lots — **31% faster** (averaged over 15
seeds). This is a textbook scheduling-theory result: **priority rules only matter under contention.**
Claiming "I implemented hot-lot priority dispatching" only means something if you can also explain the
precondition under which it actually does anything.

## 5. Transport Delay Prediction (`notebooks/08_amhs_delay_prediction.ipynb`)

Simulations were run across 25 combinations of vehicle count (3–8) × launch interval (80–220s) to
gather transport logs under varied load, then a model was trained to predict — **using only information
available at the moment a transport request is raised** — how long it will take (regression) and
whether it's at risk of delay (classification). Validation uses a run-level split (entire
vehicle-count/launch-interval combinations held out as test), to check whether the model generalizes to
load conditions it has never seen.

| Metric | Value |
|---|---|
| Cycle-time regression MAE | 57.8s (18.8% of test-set mean) |
| Cycle-time regression R² | 0.933 |
| Delay classification F1 | 0.947 |
| Delay classification AUROC | 0.996 |

**Feature importance: `concurrent_requests` (system load at request time) 0.726, `n_vehicles` 0.260,
`direct_travel_time` (static distance) 0.000.** In other words, how long a transport takes is almost
entirely explained by how busy the system is *right now*, not by the distance between stations. The
layout is fixed, but load changes in real time — which suggests a real MCS should weight live queue
state far more heavily than static routing distance.

## 6. Vehicle Predictive Maintenance (`notebooks/09_amhs_predictive_maintenance.ipynb`)

The exact same pipeline used on SECOM (`03_modeling.ipynb`: Isolation Forest + XGBoost ensemble, 5-fold
OOF threshold tuning, SHAP), reapplied unchanged to OHT vehicle sensor data (motor current, hoist
vibration, motor temperature, brake response time, bearing temperature).

| Model | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| Isolation Forest | 0.950 | 1.000 | 0.974 | 1.000 |
| XGBoost | 1.000 | 0.989 | 0.995 | 1.000 |
| Ensemble | 0.950 | 1.000 | 0.974 | 1.000 |

These numbers are much higher than SECOM's (F1 0.228), and not because the model got better — a rule-based synthetic dataset with 5 sensors is a fundamentally easier separation problem than 590 noisy real sensors (same pattern seen in notebooks 05/06). The point of this notebook isn't the number — it's showing that **the pipeline validated on SECOM transfers cleanly to a different domain** (process quality → vehicle health) without modification. Unlike a typical portfolio notebook, this model doesn't stop at offline evaluation — it's actually wired into the notebook 07 simulation via `amhs/maintenance.py`; see the "predictive-maintenance feedback" result in §4.

## 7. Interview Talking Points

> Before an AMHS-track interview, I wanted to actually understand real fab transport flow, so I built OHT/stocker/dispatching concepts as a working simulation rather than just studying them on paper.
> I modeled OHT vehicles moving between 8 process stations in SimPy, used each tool's own queue length as stocker occupancy, and reproduced back-pressure — congestion downstream propagating upstream when a buffer fills. That led to a concrete result consistent with lean manufacturing principles: a smaller stocker actually shortens average transport time, because it caps how much WIP the system carries at once.
> Beyond nearest-vehicle/FCFS/zone-based dispatching, I built an adaptive policy that predicts transport delay in real time and switches to zone-based dispatching under predicted congestion. The delay-prediction model, trained on simulation logs, showed that real-time system load at request time — not static inter-station distance — is by far the strongest predictor of delay, which suggests a real MCS should weight live queue state over static routing.
> I also reapplied the Isolation Forest/XGBoost ensemble I built for SECOM anomaly detection to OHT vehicle motor and vibration sensor data, and — instead of stopping at an offline evaluation — actually wired that predictive-maintenance model into the live simulation. With it enabled, average transport time got about 6.7% worse, concretely demonstrating the AMHS-specific risk that a single vehicle failure cascades into broader congestion.
> Finally, since real fabs don't treat every lot equally, I implemented hot-lot priority dispatching. The interesting part was that priority made zero difference when vehicles had spare capacity — it only started to matter once I deliberately created contention (fewer vehicles, denser request arrivals), at which point hot lots came out 31% faster than normal lots. That's scheduling theory's core principle — priority rules only matter under resource contention — confirmed directly through simulation rather than just cited from a textbook.

## 8. References

The dispatching policies in this project (nearest/FCFS/zone-based/hot-lot/predictive) were designed independently rather than derived from a specific paper. To understand where that design overlaps with — and diverges from — actual published AMHS research, the following were reviewed:

| # | Reference | Relation to this project |
|---|---|---|
| ① | Agrawal, G., & Heragu, S. (2006). *A Survey of Automated Material Handling Systems in 300-mm Semiconductor Fabs.* IEEE Transactions on Semiconductor Manufacturing, 19(1), 112–120. | A concept map of AMHS as a whole (stocker, OHT, layout, dispatching) — the basis for the terminology used in §1–3. |
| ② | Liao, D.-Y., & Wang, C.-N. (2005). *Differentiated preemptive dispatching for automatic materials handling services in 300 mm semiconductor foundry.* The International Journal of Advanced Manufacturing Technology (Springer). | Real published research on **hot-lot priority dispatching** (the DPD policy), validated against actual data from a 300mm Taiwanese foundry. The hot-lot logic in `amhs/simulation.py` is far less sophisticated than this paper — it reorders the waiting queue rather than doing true preemption — but tackles the same underlying problem. |
| ③ | Wang, C.N., Wang, J.W., Chou, M.T., Liao, R.Y., & Huang, C.J. (2017). *A dispatching method for the lots of different priorities in 450-mm semiconductor manufacturing.* Advances in Mechanical Engineering (SAGE). | Further evidence that lot-priority dispatching is a persistent, actively studied problem in academia, not just an industry footnote. |
| ④ | Im, S. et al. *Effective overhead hoist transport dispatching based on the Hungarian algorithm for a large semiconductor FAB.* | This project's nearest/zone-based policies assign vehicles greedily, one request at a time. Real research explores globally optimal vehicle-request matching via the **Hungarian algorithm** — a natural next step for making this project more sophisticated. |
| ⑤ | *Multi-factor OHT scheduling method of AMHS for semiconductor fabrications.* | Multi-factor scheduling that jointly weighs distance, wait time, lot priority, bottleneck stations, and vehicle utilization. This project handles each factor as a separate policy (nearest = distance, hot lot = priority, predictive = congestion) instead of one unified cost function — combining them would move this project closer to this direction. |
| ⑥ | *Multiagent reinforcement learning-based dispatching model for overhead hoist transfer in AMHS* (2025, ScienceDirect). | Recent research has moved past rule-based dispatching toward reinforcement learning. `amhs/predictive.py` (a supervised regression model predicting congestion to trigger a policy switch) is a much simpler precursor to this direction. |

**An honest limitation**: this project's dispatching policies are considerably simpler than the literature above (greedy assignment, no global optimization; the "predictive" policy is a single regression model gating a threshold, nothing close to real RL). The reason for reviewing this literature wasn't to make the simulation look more sophisticated than it is — it was to confirm, honestly, that this project simplifies a *real* studied problem rather than inventing a plausible-sounding one, and to have concrete next steps in mind (Hungarian algorithm, multi-factor cost functions, RL) for making it more sophisticated later.
