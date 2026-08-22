# NetGravity — AI Decision Intelligence for Supply Chain & Logistics Networks

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MILP Core](https://img.shields.io/badge/Solver-PuLP%20%7C%20HiGHS%20%7C%20CBC-purple.svg)](https://github.com/coin-or/pulp)
[![Tests](https://img.shields.io/badge/Automated%20Tests-304%20Passing-brightgreen.svg)](netgravity/tests/)
[![Architecture](https://img.shields.io/badge/Architecture-Deterministic%20MILP%20%2B%20Governed%20Orchestrator-orange.svg)](#3-system-architecture)

> **NetGravity** is an enterprise-grade decision-intelligence and network optimization platform for logistics networks. It joins mathematically rigorous Mixed-Integer Linear Programming (MILP) with automated ingestion, multi-model AI forecasting, and a governed AI control plane — keeping a hard boundary between mathematical truth and generative reasoning.

---

## 1. The Core Paradigm

Supply chain tools usually force a choice: solvers that are rigorous but opaque, or AI dashboards that are fluent but unverifiable. NetGravity eliminates the trade-off by making the boundary explicit and enforcing it in code.

**One rule governs the whole system:**

> The MILP solver, the REI engine, and the RF calculator are the only sources of numeric truth. A language model may interpret requests, parse unstructured contracts/news, and explain results. It may never produce, adjust, or replace an optimization number.

Three mechanisms enforce that rule in code:

| Mechanism | What it prevents |
|---|---|
| **Read-only evidence** | The reasoning agent receives already-computed results and has no write path back to the optimizer. |
| **Numeric-claim grounding** | Every figure in generated narrative is adjudicated against authoritative solver values. Contradicted and unsupported numbers are **removed from the text**, not merely flagged. |
| **Proposal validation** | Model-suggested facilities and scenarios are validated against canonical master data; a hallucinated site fails validation before the solver ever runs. |

A fourth principle runs through everything: **missing is not zero.** When exposure, probability, or risk cannot be computed, the system reports *why* it could not rather than substituting a default value, and missing evidence withholds automation — it can never grant it.

---

## 2. What Is Built

| Capability | Status |
|---|---|
| **Deterministic MILP Core** (multi-echelon, capacitated, inventory-aware) | **Mature** — 100% cost reconciliation, benchmark-anchored |
| **Data Ingestion & Sanitization Pipeline** (`netgravity.ingestion`) | **Complete** — Auto-column mapping, rate-card PDF parser, geo-imputation |
| **AI Forecasting Engine** (`netgravity.forecasting`) | **Complete** — ADI vs $CV^2$ auto-characterization, Croston/SBA, LightGBM Quantile ($P_{10}/P_{50}/P_{90}$), AutoETS, TimesFM/Chronos adapter |
| **Facility Resilience Assessment + Risk Exposure Index (REI)** | **Complete**, cached, and persisted |
| **Risk Factor (RF) Calculation** from external event probability | **Complete**, with explicit refusal semantics ($RF = P + REI - P \cdot REI$) |
| **Orchestrator Control Plane** (planning, dependencies, governance, audit) | **Complete** |
| **Conversational Layer** (chatbot → NLU → orchestrator) | **Complete** |
| **Interactive Web Cockpit & Digital Twin** | **Complete** demonstration build on Case-16 fixture |

---

## 3. System Architecture

```
                          ┌────────────────────────────────────────────────────────┐
                          │               1. DATA SOURCES & INGESTION              │
                          │   ERP / Excel, Rate Cards, Search & Disruption Signals │
                          └──────────────────────────┬─────────────────────────────┘
                                                     │
                   ┌─────────────────────────────────┴─────────────────────────────────┐
                   ▼                                                                   ▼
┌─────────────────────────────────────┐                             ┌─────────────────────────────────────┐
│     2. AI FORECASTING ENGINE        │                             │      3. ORCHESTRATOR CONTROL PLANE  │
│ • ADI vs CV² Auto-Characterizer     │                             │ • Receives user intent / chat       │
│ • Multi-Model: Croston, LightGBM,   │                             │ • Workflow Graph & Dependency State │
│   AutoETS, Zero-Shot Foundation     │                             │ • Enforces Governance & Precedence  │
│ • Low-Token External Signal Fuser   │                             └──────────────────┬──────────────────┘
│ • Generates P10, P50, P90 & σ_D     │                                                │
└──────────────────┬──────────────────┘                                                │
                   │                                                                   │
                   └─────────────────────────────────┬─────────────────────────────────┘
                                                     ▼
                          ┌────────────────────────────────────────────────────────┐
                          │                  4. MILP SOLVER CORE                   │
                          │          (Deterministic Source of Numeric Truth)       │
                          │  • Facility Location (y_i ∈ {0,1})                     │
                          │  • Multi-Commodity Flow Routing (x_ijvk)               │
                          │  • Linear Precomputed Safety Stock Cost (IC_ij a_ij)   │
                          │  • Single-Pass HiGHS / CBC Exact Solution              │
                          └──────────────────────────┬─────────────────────────────┘
                                                     │
                   ┌─────────────────────────────────┴─────────────────────────────────┐
                   ▼                                                                   ▼
┌─────────────────────────────────────┐                             ┌─────────────────────────────────────┐
│       5. RESILIENCE & RISK (REI/RF) │                             │      6. REASONING & DIGITAL TWIN    │
│ • Disruption Simulation (PI / EI)   │                             │ • Digital Twin (Baseline vs Peak)   │
│ • Risk Exposure Index (REI)         │                             │ • Numeric Claim Grounding Engine    │
│ • RF = P + REI − (P × REI)          │                             │ • Tier-Based Actioning (Auto/HITL)  │
└─────────────────────────────────────┘                             └─────────────────────────────────────┘
```

---

## 4. AI Forecasting Engine (`netgravity.forecasting`)

The forecasting module converts historical time-series, contractual terms, and external web signals into multi-period, uncertainty-aware parameters consumed by the MILP solver and Scenario Planner.

### Key Capabilities

#### A. Demand Pattern Auto-Characterization (ADI vs $CV^2$)
Every SKU time-series is classified across the standard **Syntetos-Boylan demand matrix**:
* **Smooth** ($ADI < 1.32, CV^2 < 0.49$): High predictability, regular continuous demand.
* **Intermittent** ($ADI \ge 1.32, CV^2 < 0.49$): Sporadic demand with constant sizing.
* **Erratic** ($ADI < 1.32, CV^2 \ge 0.49$): Continuous demand with volatile sizing.
* **Lumpy** ($ADI \ge 1.32, CV^2 \ge 0.49$): Sporadic demand with extreme sizing variance.
* **Cold-Start** ($N < 8$ observations): Sparse or newly launched SKUs.

#### B. Specialized Multi-Model Engines ($0 API Token Cost)
* **Croston's Method & Syntetos-Boylan (SBA)**: Decouples non-zero demand size from arrival interval, eliminating over-forecasting and inventory bloat on spare parts.
* **LightGBM / Quantile Regressor**: Generates exact $P_{10}, P_{50}, P_{90}$ forecast bounds via Linear Programming (Highs Pinball Loss) with lag, trend, and cyclic seasonality features.
* **Auto-ETS (Exponential Smoothing)**: Holt linear trend & Holt-Winters seasonal smoothing with automated parameter grid search and analytical prediction intervals.
* **Pre-Trained Foundation Model Adapter**: Zero-shot inference for cold-start SKUs leveraging **Google TimesFM** and **Amazon Chronos** with Bayesian prior fallback.
* **Auto-Model Selector**: Dynamically routes each time-series to the mathematically optimal engine.

#### C. Surgical Low-Token Signal Fuser
* Extracts structured impact multipliers from external search trends, weather alerts, or carrier strikes in a **single compact prompt** or deterministic semantic keyword fallback.
* Modulates baseline demand and volatility into bounded multipliers ($k_{\text{demand}} \in [0.5, 2.0]$, $k_\sigma \in [0.8, 3.0]$) at minimal API cost.

#### D. Direct MILP Bridge
* Directly generates `DemandRecord` instances matching `CanonicalNetwork`.
* Injects standard deviation $\sigma_D$ into `InventoryCoefficientEngine` to optimize safety stock holding costs ($IC_{ij} = z \cdot \sigma_D \cdot \sqrt{L_{ij}} \cdot h$).
* Produces `p10_conservative`, `p50_expected`, and `p90_surge` network variants for robust optimization.

---

## 5. The Deterministic Core (MILP, REI & RF)

### MILP Objective Function

$$\min \sum_{i \in \mathcal{F}} f_i y_i + \sum_{(i,j) \in \mathcal{A}} \sum_{p \in \mathcal{P}} c_{ijp} x_{ijp} + \sum_{i \in \mathcal{F}, j \in \mathcal{M}} IC_{ij} a_{ij} + \sum_{i} \text{closure}_i (1 - y_i) + \lambda_{\text{carbon}} \sum_{(i,j)} e_{ij} x_{ij} + \text{Penalties}$$

Subject to:
1. **Demand Satisfaction**: $\sum_{i, v} x_{ijvp} + u_{jp} = D_{jp} \quad \forall j \in \mathcal{M}, p \in \mathcal{P}$
2. **Facility Capacity Ceiling**: $\sum_{j, v, p} x_{ijvp} \le \text{Cap}_i y_i \quad \forall i \in \mathcal{F}$
3. **Single-Pass Inventory Assignment**: $a_{ij} \le y_i$ and $\sum_{v, p} x_{ijvp} \le D_j a_{ij}$
4. **Echelon Mass Balance**: Inbound Flow = Outbound Flow at each intermediate DC
5. **SLA Delivery Thresholds**: Strict transit lead-time compliance by priority tier

> **Solver objective ≠ business cost.** The shortage penalty (default `1e6`/unit) is a mathematical device that forces demand coverage, not a financial cost. Business Network Cost excludes it. Every REI figure is computed on reconciled *business* cost.

### Validated Benchmarks
- **Hand-Solvable 2-DC Reference Case**: Evaluates to **`$5,400.00`** (Optimal facility: `DC_T1`).
- **Kearney Case 16 Full Network**: Evaluates to **`$115,638.14/month`** with 100% cost reconciliation.

### Resilience Assessment: REI & RF

* **Performance Impact**: $PI(k) = \text{Cost}(k) - \text{Cost}_0$
* **Economic Impact**: $EI(k) = \max(0, PI(k))$
* **Risk Exposure Index**: $REI(k) = \frac{EI(k)}{\max_j EI(j)}$
* **Risk Factor (RF)**:
  $$RF = P + REI - (P \times REI)$$

`P = 0` is a measurement and computes normally ($RF = REI$). A missing $P$ is an absence and returns `NOT_COMPUTABLE` — severity is never substituted for probability.

---

## 6. Conversational Layer & Governance

```
USER → CHATBOT → NLU → STRUCTURED INTENT → ORCHESTRATOR → workflow → engines
                        ↑ the LLM stops here
```

The model's influence ends at an `Intent` enum value. It cannot name a workflow, a capability, or a step; `WorkflowPlanner` alone maps intent to graph.

### Three Structural Enforcement Guarantees:
1. `ConversationalIntent` has **no field** able to hold a cost, REI, RF, SLA, or governance outcome.
2. Every entity ID comes from `CanonicalNetwork.facilities`; no code path produces an identifier from user text.
3. Language modules are scanned for engine imports by automated tests to ensure no direct solver invocation.

### Action Governance Precedence
* **Structural actions (e.g. facility closure) are `HUMAN_ONLY` regardless of REI, RF, or cost.** Irreversibility governs, not exposure.
* **Missing critical evidence withholds automation** (`R7B`). Absent risk information is never read as absence of risk.
* **Failed numeric grounding withholds automation** (`R7C`): an explanation that cannot be verified cannot justify an action.

---

## 7. Repository Structure

```
NetGravity/
├── README.md                          # Master architectural documentation
├── requirements.txt                   # Production dependencies
├── pyproject.toml                     # Package metadata & test config
├── smoke_test.py                      # Fast verification suite (< 2s execution)
├── run.py                             # Web application launcher
│
├── app/                               # 🌐 Interactive Web Cockpit & Digital Twin
│   ├── backend/app.py                 # Flask API & telemetry endpoints
│   ├── frontend/                      # Decision cockpit, Leaflet map, Chart.js views
│   └── standalone/                    # Portable zero-dependency single-file HTML build
│
├── docs/                              # 📚 Architecture & Mathematical Docs
│   ├── mathematical_model.md          # Full MILP formulation
│   ├── model_architecture.md          # Echelon architecture & pipeline
│   ├── facility_resilience_rei.md     # REI & Risk Factor methodology
│   └── *.md                           # Validation reports & phase audit trails
│
├── netgravity/                        # ⚡ Core Platform Package
│   ├── forecasting/                   # 📈 Hybrid AI Forecasting Engine
│   │   ├── agent.py                   # ForecastingAgent coordinator
│   │   ├── schemas.py                 # TimeSeries & ForecastResult schemas
│   │   ├── characterizer.py           # ADI vs CV² demand categorization
│   │   ├── engines/                   # Croston, Quantile, ETS, Foundation models
│   │   ├── signals/                   # Low-token external signal fusers
│   │   ├── bridge/                    # MILP & Scenario network bridge
│   │   └── tests/                     # Forecasting test suite (15 tests)
│   │
│   ├── ingestion/                     # 📥 Data Ingestion & Sanitization Pipeline
│   │   ├── pipeline.py                # Ingestion runner
│   │   ├── builder.py                 # CanonicalNetwork assembler
│   │   ├── adapters/                  # Excel, CSV, PDF rate-card parsers
│   │   ├── ai/                        # Column mapper & structured sanitizers
│   │   └── guardrails/                # External signal policy enforcement
│   │
│   ├── optimization/                  # 📐 Mathematical Optimization Core (MILP)
│   │   ├── milp.py                    # Direct V1.2 formulation & solve logic
│   │   ├── solver.py                  # PuLP, HiGHS, CBC solver interfaces
│   │   └── baseline.py                # Baseline network cost evaluation
│   │
│   ├── orchestrator/                  # ── Governed Control Plane ──
│   │   ├── core/                      #    Planner, execution context, state
│   │   ├── engines/                   #    Deterministic adapters, scenario builder
│   │   ├── agents/                    #    Intent, reasoning, LLM gateway
│   │   ├── risk/                      #    RF calculator & event assessment
│   │   ├── validation/                #    Numeric grounding & claim checks
│   │   └── governance/                #    Action classifier & approval policies
│   │
│   ├── inventory/                     # Safety stock, cycle stock & coefficient engine
│   ├── resilience/                    # REI disruption engine, cache & persistence
│   ├── scenarios/                     # Scenario execution & sweeps
│   └── tests/                         # Master test suite
│
└── scripts/build_standalone.py        # Automated single-file HTML compiler
```

---

## 8. Quickstart Guide

### Prerequisites
- Python 3.10 or higher
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Installation
```bash
# 1. Clone repository
git clone https://github.com/Rajat-star/NetGravity.git
cd NetGravity

# 2. Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Fast smoke verification (~2s)
python smoke_test.py

# Run complete automated test suite
pytest

# Run forecasting test suite specifically
pytest netgravity/forecasting/tests -v
```

### Running the Web Application
```bash
# Launch web application (recommended)
python run.py
```
Open [http://localhost:5050](http://localhost:5050) in your web browser.

**Zero-Dependency Offline HTML Demo**: Open `app/standalone/netgravity_standalone.html` directly in any web browser without needing a Python or Node environment.

---

## 9. Attribution & License
Developed for the **Kearney Case Competition** (Case 16 — Interactive Logistics Network Optimisation Agent). Proprietary decision-intelligence and mathematical optimization architecture.
