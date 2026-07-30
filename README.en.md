# 🏭 SemiSense — Semiconductor Process Simulator & Fault Detection AI

[![tests](https://github.com/heeannw/semiconductor-fault-detection/actions/workflows/tests.yml/badge.svg)](https://github.com/heeannw/semiconductor-fault-detection/actions/workflows/tests.yml)

*[한국어 버전(Korean)](README.md)*

A portfolio project simulating an 8-stage semiconductor fab process and detecting process anomalies with AI in near real time. Originally built while applying to Korean semiconductor manufacturers, then extended for AMHS (Automated Material Handling System) roles and for applications to equipment/materials-handling companies more broadly (e.g. Applied Materials, ASML, Lam Research, KLA).

- **Timeline:** 6 weeks initial build, extended over several follow-up sessions
- **Dataset:** SECOM (UCI)
- **Stack:** FastAPI + React + SimPy + scikit-learn/XGBoost

## 📌 Project Overview

Two independent axes live in this repository, on purpose:

| Component | Role | Note |
|---|---|---|
| SECOM dataset | AI model training & evaluation | Public UCI dataset, real semiconductor process sensor readings |
| Process simulator | Synthetic data for real-time inference | Synthetic data generated from 8 process stages with real units/spec ranges |

SECOM has no label indicating which fab process each row came from, so the two modules are deliberately kept separate rather than wired together end-to-end. This is a design decision worth being able to explain, not an oversight — it comes up in interviews.

### AMHS extension (built for an SK hynix AMHS-track application)

If the SECOM/process-simulator part answers **"is this wafer defective?"** (FDC — Fault Detection and Classification), `amhs/` and `notebooks/07–09` answer **"does this wafer arrive at the next tool on time?"** (AMHS — material handling). It covers OHT (Overhead Hoist Transport) dispatch simulation, dispatch-policy comparison, transport-delay prediction, and vehicle predictive maintenance, plus a live "AMHS" screen in the dashboard. Full write-up: [docs/AMHS.en.md](docs/AMHS.en.md).

### Yield-to-cost quantification framework (`notebooks/11_cost_sensitive_threshold.ipynb`)

F1/AUROC are engineering metrics. The people who actually decide whether an FDC model is worth deploying — process managers, quality directors — think in terms of cost: "how much does this save us per month?" This notebook reinterprets the SECOM ensemble's confusion matrix in cost terms (false positive = re-inspection cost, false negative = escaped-defect cost) and shows that the cost-optimal decision threshold is not the same as the F1-optimal one.

**Caveat, stated explicitly**: the dollar figures used (re-inspection cost, escape cost) are illustrative placeholders, not real cost data from any company — that data is proprietary and this project has no access to it. What the notebook actually demonstrates is not a specific dollar figure but a **reusable structure**:

1. A first pass swept thresholds on an evenly spaced grid (0.01–0.99) and found an "optimum" sitting right at the grid floor. Widening the search to the full set of observed probabilities revealed the true optimum was much lower (~0.0014) — and at that threshold, ~90% of the test-set wafers would be flagged for re-inspection. Mathematically correct given the assumed 50:1 FN:FP cost ratio, operationally absurd.
2. So a re-inspection capacity constraint was added — "the re-inspection line can't handle more than N% of wafers." At a 10% capacity cap the optimal threshold is 0.1115, and the cost-vs-capacity curve shows sharply diminishing returns past ~10%.
3. An honest negative result was kept in, not smoothed over: on the test set (only 21 positive samples), the capacity-10%-constrained threshold actually costs *more* than the plain F1-optimal one. At this sample size, policy rankings aren't stable. The point of the framework isn't "our method wins" — it's that **F1 optimization, cost optimization, and operational constraints (capacity) are three different questions that change the answer in sequence.**

## 📚 Reference Papers & Datasets

### Core papers

| # | Title | Source | Key technique |
|---|---|---|---|
| ① | Anomaly Detection and Classification Using Semiconductor Process Monitoring Data | KISTI | Fuzzy model + Dempster-Shafer theory, OES sensors |
| ② | Cross Multi-Task Learning for Anomaly Detection | Seoul National University | CNN + self-attention, multivariate time series |
| ③ | Equipment Fault Detection via Correlation Analysis and Data Augmentation | DBpia | Grad-CAM, feature matrices, data augmentation |
| ④ | Feature-Based Decision Trees for Anomaly Detection and Classification | KISTI | Decision Tree, feature-selection methodology |
| ⑤ | Process Anomaly Detection Using Smart Factory Big Data | KISTI | FDA, ML accuracy comparison |

PDFs (Korean-language originals) stored under `docs/papers/`.

### Public datasets

1. **SECOM Dataset (primary)** — [archive.ics.uci.edu/dataset/179/secom](https://archive.ics.uci.edu/dataset/179/secom)
   - Real semiconductor manufacturing process sensor data
   - 590 features, 1,567 samples
   - ~93% pass / ~7% fail (severe class imbalance, handled explicitly)
   - Many features have >50% missing values
2. **WM-811K Wafer Map** — [kaggle.com/datasets/qingyi/wm811k-wafer-map](https://www.kaggle.com/datasets/qingyi/wm811k-wafer-map) (optional extension)
3. **MIMII Dataset** — [zenodo.org/record/3384388](https://zenodo.org/record/3384388) (optional extension, not used yet)

### Reference GitHub repos

- [hoya012/awesome-anomaly-detection](https://github.com/hoya012/awesome-anomaly-detection)
- [yzhao062/pyod](https://github.com/yzhao062/pyod)

## 🏗️ System Architecture

```
[React frontend]
    ↕ REST API
[FastAPI backend]
    ↕                         ↕
[AI model server]         [SQLite DB]
 Isolation Forest          process logs
 XGBoost                   fault records
 (LSTM Autoencoder)        sensor data
    ↕
[Process simulator]
 Synthetic data from 8 process stages
 → real-time inference via trained models
```

## 🛠️ Tech Stack

| Area | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| AI/ML | scikit-learn, XGBoost, SHAP, PyTorch (LSTM/CNN notebooks) |
| Frontend | React (Vite) + Recharts |
| DB | SQLite |
| Discrete-event simulation | SimPy (AMHS) |
| Deployment | Docker (backend + frontend), GitHub Actions CI |

## 📁 Project Structure

```
semiconductor-fault-detection/
├── data/
│   ├── raw/            # Raw SECOM data (not tracked in git)
│   └── processed/      # Preprocessed data
├── docs/
│   ├── papers/         # Reference paper PDFs
│   ├── AMHS.md          # AMHS concept write-up (Korean)
│   └── AMHS.en.md        # AMHS concept write-up (English)
├── notebooks/          # EDA and experiment notebooks
├── simulator/           # 8-process synthetic data generator + SPC
├── amhs/                # OHT dispatch simulation, dispatching, predictive maintenance
├── models/              # Trained model artifacts
├── backend/
│   ├── app/              # FastAPI server
│   ├── requirements.txt   # Slim runtime-only dependencies (for the Docker image)
│   └── Dockerfile
├── frontend/            # React dashboard
│   └── Dockerfile
└── docker-compose.yml   # Run backend + frontend locally
```

## 🔬 What's implemented

### 1. Data & preprocessing

- Missing-value pattern analysis; features with >50% missing values dropped (28 of 590)
- Median imputation for the rest, zero/low-variance features dropped, `StandardScaler`
- Class imbalance handled with SMOTE (train split only) and `class_weight='balanced'`; evaluated with F1/AUROC, never raw accuracy

### 2. Process simulator (`simulator/process_simulator.py`)

A synthetic data generator based on 8 process stages with real units and spec ranges. It is **not** wired to SECOM — SECOM has no per-process label, so the two are kept as independent modules that both feed the same downstream API shape.

| Process | Key parameters | Normal range |
|---|---|---|
| ① Wafer fabrication | Temperature, oxygen concentration, resistivity | 1400–1500 °C, 0–10 ppb, 1–100 Ω·cm |
| ② Oxidation | Temperature, time, oxide thickness | 900–1200 °C, 10–120 min, 10–1000 nm |
| ③ Photolithography | Exposure energy, focus, temperature | 10–50 mJ/cm², ±0.1 μm, 90–130 °C |
| ④ Etching | Pressure, gas flow, power | 5–100 mTorr, 10–200 sccm, 100–2000 W |
| ⑤ Deposition | Temperature, pressure, deposition rate | 300–900 °C, 0.1–10 Torr, 1–100 nm/min |
| ⑥ Metallization | Current density, temperature, plating time | 1–10 mA/cm², 20–80 °C, 1–30 min |
| ⑦ EDS (electrical die sort) | Test voltage, current | 1–5 V, 1–100 μA |
| ⑧ Packaging | Dicing speed, bond strength, temperature | 10–100 mm/s, 5–15 g, 150–180 °C |

Anomalies are generated by pushing parameters outside their normal range, at roughly a 10% anomaly rate.

### 3. Anomaly detection models (`notebooks/03_modeling.ipynb`)

- **Isolation Forest** (unsupervised): `contamination=0.07`, threshold on anomaly score
- **XGBoost** (supervised): binary classification with `scale_pos_weight`, top-20 feature importance, SHAP explainability
- **Ensemble**: vote (flag if either model flags — recall-first design) or weighted score average
- **LSTM Autoencoder** (extension, `notebooks/05_lstm_autoencoder.ipynb`): reconstruction-error anomaly detection on the simulator's synthetic time series

#### Results (test set, 314 samples, evaluated exactly once)

| Model | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| Isolation Forest | 0.214 | 0.143 | 0.171 | 0.541 |
| XGBoost | 0.155 | 0.429 | 0.228 | 0.692 |
| Ensemble (vote, recall-first) | 0.156 | 0.476 | 0.235 | 0.612 |

- The XGBoost classification threshold was tuned with 5-fold cross-validated out-of-fold (OOF) predictions on the dev split — **never on the test split**, to avoid threshold leakage.
- SECOM is a well-known benchmark with weak label-feature correlation and heavy sensor noise; this F1/AUROC range is consistent with published prior work on the same dataset.
- The ensemble is intentionally recall-first: it catches 10 of 21 real defects (47.6%) at the cost of more false positives, on the reasoning that a missed defect is more expensive than a false alarm — a reasoning made explicit and quantified in the [cost framework](notebooks/11_cost_sensitive_threshold.ipynb) above.

#### SHAP explainability

`shap.TreeExplainer` adds global and local explanations to the XGBoost model:

- Global: `shap.summary_plot` (bar + beeswarm) over the top 20 features, cached to `models/shap_importance.joblib`.
- Local: per-sample, signed feature contributions toward "anomaly" vs. "normal." Served live via `POST /api/ai/explain`, using the same tree structure the model used to make the prediction — so notebook and API results match exactly.
- Rendered as colored bars (red = pushes toward anomaly, green = pushes toward normal) on the anomaly-detection screen in the dashboard.

#### Cpk/Ppk & SPC control charts (`simulator/spc.py`, `notebooks/10_spc_process_capability.ipynb`)

Separate from the ML-based detector: this covers the most basic tool of fab quality control — **SPC** (control charts, process capability indices, Western Electric rules). SECOM's features are anonymized with no units, so Cpk is meaningless there; instead this was applied to the process simulator, which has real units and spec limits.

- **Cpk distribution**: of 21 process parameters, 15 are "not capable" (Cpk < 1.0), 8 are "capable but needs monitoring," average Cpk 0.991 — an expected result given the simulator draws from `(high−low)/6` as its standard deviation, i.e. it deliberately mimics a fab running with little margin.
- **Western Electric rule detection** (etching chamber pressure, evaluated on a held-out anomaly stream): precision 0.684, **recall 1.0**, F1 0.813 — the simulator's injected anomalies clearly leave the normal range, so a classic 3-sigma control chart catches nearly all of them.
- SECOM's ML result (F1 0.228) isn't directly comparable (different data), but the contrast illustrates a real distinction: **SPC is simple, explainable rule-based detection; ML learns multivariate patterns.** In practice, fabs often start a new process with SPC and layer ML on top once enough data accumulates.

#### Root-cause label + cause/impact/fix suggestion (rule-based, `simulator/diagnosis.py`)

The original goal of this project was a pipeline that goes "detect anomaly → why → what happens if left alone → how to fix it." SHAP (above) shows which features drove a SECOM verdict, but SECOM's features are anonymized (`feature_1`, `feature_2`, ...), so there's no way to turn that into a human-readable diagnosis — an inherent limitation of the dataset, not something this project can fix. The process simulator's parameters, on the other hand, have real names, units, and spec ranges, so "this parameter went out of spec in this direction" is enough on its own to look up a semiconductor-process-domain-informed cause, impact, and suggested fix, as a static rule.

- **No LLM API calls at all** — all 8 processes × 24 parameters × 2 directions (48 combinations total) are pre-written as static templates. Fully deterministic, zero cost.
- `simulator/tests/test_diagnosis.py` includes a completeness test asserting all 24 parameters × 2 directions are mapped — if even one template were missing, a reading would show "anomaly" with no cause or fix, a silent blind spot this test exists to catch.
- Exposed via the `diagnoses` field on `POST /api/process/simulate` / `/api/process/status` / `/api/process/history`; the `ProcessCard` component on the dashboard shows a per-parameter root-cause label, likely cause, downstream impact if left unaddressed, and suggested action whenever a reading is anomalous.

#### AI-based fault classifier (learned from data, not hardcoded — `notebooks/12_fault_scenario_classification.ipynb`)

The rule-based diagnosis above checks each parameter independently — it has no notion that "pressure and gas flow are both off because they share one underlying cause." This notebook closes that gap: `simulator/fault_scenarios.py` synthetically generates labeled data where a hidden root cause (e.g., MFC calibration drift) shifts multiple parameters together in a correlated pattern, and XGBoost is trained per process to infer the cause from that pattern alone — a judgment learned from data, not a hardcoded if-statement.

- **81–87% accuracy across all 8 processes** (3-class: normal + 2 scenarios each). Not directly comparable to SECOM (F1 0.235) for the same reason as always — this is rule-generated synthetic data, SECOM is real noisy sensor data.
- **An honest finding along the way**: wiring this model into the dashboard's default "Generate Data" button (which perturbs each parameter independently and at random) produced mostly "normal" predictions even when values were clearly out of spec — the injected pattern simply didn't match anything the classifier was trained on. Rule-based diagnosis and the AI classifier answer **different questions**: the rule asks "is this one parameter out of spec," the AI asks "does this multi-parameter pattern resemble a fault signature I was trained on." So a dedicated demo path was added (`POST /api/process/fault-demo`, the "AI Fault Classification Demo" card on the dashboard) that injects the actual trained correlated patterns to show what the classifier is genuinely good at. First validated this with 30 samples and got a worrying 60% — re-checked with 200 samples and got 83.5%, confirming it was small-sample noise, not a real regression (the corresponding test was fixed to use n=150 / threshold 0.65 accordingly).
- Also wired into `POST /api/process/simulate` and friends via a `predicted_fault` field, shown side-by-side with the rule-based diagnosis on the `ProcessCard` component.

#### Feature selection experiment (`notebooks/04_feature_selection.ipynb`)

Tested whether a correlation filter (|corr| > 0.95 removed, 440→267 features) plus XGBoost-importance-based selection could beat the 440-feature baseline. Each candidate K (30/50/100/200/267) was tuned with the same 5-fold OOF procedure as the baseline model, and only the OOF-best (k=30) was evaluated on test, once.

| | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| Baseline (k=440) | 0.155 | 0.429 | **0.228** | 0.692 |
| Feature-selected (k=30) | 0.129 | 0.190 | 0.154 | **0.741** |

**Conclusion: keep the k=440 baseline in production.** AUROC (ranking quality) clearly improved, but F1 got worse — with only 83 positive samples in the dev split, the OOF-selected threshold was sensitive to fold noise and didn't transfer well to test recall. The bottleneck is threshold calibration, not feature count. Next step: target-recall thresholding, or averaging thresholds across folds instead of taking the argmax. Full grid in `models/feature_selection_grid.csv` / `feature_selection_comparison.csv`.

#### LSTM Autoencoder (`notebooks/05_lstm_autoencoder.ipynb`)

Completely separate from SECOM: an LSTM Autoencoder trained only on normal patterns from the simulator's synthetic time series (length-10 windows, one model per process), using reconstruction error to flag anomalies.

- **First attempt (mean reconstruction error over the whole window) performed poorly** — F1 0.18–0.22 per process. Cause: only the last of 10 timesteps is actually anomalous, so averaging in 9 normal, low-error timesteps diluted the signal.
- Since the label is "is the last timestep anomalous," switching the score to **only the last timestep's reconstruction error** pushed the average F1 across 8 processes from 0.20 to **0.955**, and AUROC from 0.72 to **~1.0**.
- The simulator's anomalies are rule-generated (parameters pushed outside spec), which is a much easier separation problem than SECOM's real, noisy sensor data — that caveat matters. The real lesson from this experiment is less the headline number and more that **window-aggregation choice dominates performance in time-series anomaly detection**.
- Not wired into `backend/`/`frontend/` — kept as a notebook-level experiment by design.

#### WM-811K wafer-map defect CNN (`notebooks/06_wafer_map_cnn.ipynb`)

A third data modality after tabular (SECOM) and time series (simulator): wafer-map images.

- **Data pipeline note**: the raw `LSWMD.pkl` (pickled in 2019 under an old pandas) can't be read by modern pandas (`ModuleNotFoundError: pandas.indexes`). `scripts/convert_wm811k.py` runs once in a throwaway legacy venv (`pandas==1.5.3`) to convert the 25,519 defect-labeled wafers to 32×32 arrays, saved as `data/processed/wafer_map_defects.npz` (3 MB) — committed to git so the notebook runs on a fresh clone without needing the 2 GB raw file or the legacy venv.
- Classifies 8 defect patterns (Center/Donut/Edge-Loc/Edge-Ring/Loc/Random/Scratch/Near-full), excluding "none" (normal). Uses the dataset's built-in train/test split (17,625 / 7,894).
- Class imbalance (Near-full: 149 samples vs. Edge-Ring: 9,680 — 65x) handled via `CrossEntropyLoss` class weighting rather than image oversampling.
- 3-conv-block CNN (16→32→64 channels), 15 epochs, trains in minutes on CPU.
- **Test result: accuracy 0.605, macro F1 0.664.** Near-full (F1 0.88) and Edge-Ring (F1 0.83) are well separated; Scratch (precision 0.22) is heavily confused with visually similar Random/Loc patterns. Below published state-of-the-art on this benchmark, but a reasonable baseline from a minimal CNN + class weighting alone.
- Not wired into `backend/`/`frontend/`, same reasoning as the LSTM notebook.

### 4. FastAPI backend (`backend/`)

```
POST   /api/process/simulate   Generate process simulator data
POST   /api/ai/detect          Run anomaly detection (ensemble)
GET    /api/process/status     Current process state
GET    /api/process/history    Process history
GET    /api/fault/list         List detected anomalies
GET    /api/fault/{id}         Anomaly detail
POST   /api/alert/send         Send an anomaly alert
GET    /api/stats/summary      Overall statistics
GET    /api/stats/yield        Yield statistics
POST   /api/model/retrain      Retrain the model
GET    /api/health             Health check
```

Plus, added later for dashboard needs not in the original 11-endpoint plan:

```
GET    /api/model/metrics             Model performance history
GET    /api/model/feature-importance  Top-N XGBoost feature importance
POST   /api/ai/explain                Per-sample SHAP explanation
GET    /api/amhs/stations             AMHS transport-network station list
POST   /api/amhs/simulate             Run the OHT dispatch simulation on demand (< 1s)
```

SQLite schema: `process_logs`, `fault_records`, `model_metrics`.

Key design notes:

- `POST /api/process/simulate` and `POST /api/ai/detect` are fully decoupled. The former logs the simulator's own 3-ish physical parameters and its own normal/anomaly call to `process_logs` and never touches the SECOM-trained model. Only the latter takes SECOM-shaped 440-feature input (`models/feature_columns.joblib`) and runs the actual trained Isolation Forest + XGBoost ensemble, logging to `fault_records`. The two feature spaces have different dimensionality and cannot be connected directly — this separation is the architectural expression of the "two independent axes" design decision above.
- `POST /api/model/retrain` reuses the 5-fold OOF-tuned threshold from `notebooks/03_modeling.ipynb` (already fixed offline) and only retrains the two models on the latest `data/processed` data, overwriting `models/`.
- Run locally: `.venv/Scripts/python -m uvicorn backend.app.main:app --port 8000` (from the project root); Swagger UI at `/docs`.
- All 11 base endpoints smoke-tested with curl against real SECOM test samples and simulator data.
- Automated tests: `.venv/Scripts/python -m pytest` (from the project root). Test runs point at a separate SQLite file via `SEMISENSE_DATABASE_URL` so they never touch the real service DB (`backend/semisense.db`). ML-dependent tests are skipped automatically on a fresh clone with no `models/` directory; everything else still passes.

### 5. React dashboard (`frontend/`)

1. Main dashboard (process-status cards, anomaly overview, yield trend)
2. Process simulator screen (visualizes the 8-stage pipeline)
3. Anomaly detection results screen (feature importance, model comparison)
4. History screen (anomaly history, yield trend, model performance metrics)
5. AMHS screen (dispatch-policy comparison / vehicle-count sensitivity, run live on button click)

Key design notes:

- Vite + React + `react-router-dom` + `recharts`.
- `src/api/client.js` is the single point of contact with the backend (`http://localhost:8000`). CORS is configured on the backend to allow both the Vite dev port (5173) and the CRA-era port (3000).
- The anomaly-detection screen ships with 3 fixed real SECOM samples (normal / correctly-caught defect / missed defect) baked into `src/data/secomSamples.js`, since a human can't meaningfully hand-enter a 440-dimensional feature vector for a live demo.
- The AMHS screen calls `POST /api/amhs/simulate` live for policy comparison and vehicle-count sensitivity (feasible because the simulation runs in under a second). Delay prediction (notebook 08) and predictive maintenance (notebook 09) are shown as static reference tables instead — retraining XGBoost/Isolation Forest live on every click would be too slow for a dashboard interaction.
- The same screen also has a 2D canvas animation (`AmhsAnimation.jsx`) that replays the individual transport events from `POST /api/amhs/simulate/replay` — the 8 stations are laid out as a circular track and OHT vehicles move along their actual recorded paths. The canvas's displayed size isn't settled yet right at mount, so a `ResizeObserver` re-measures it and rescales the internal resolution once the surrounding layout actually stabilizes.
- Run locally: `cd frontend && npm install && npm run dev` (requires the backend running on port 8000).
- All 5 screens manually tested end-to-end in the browser.

### 6. Docker

```bash
docker compose up --build
```

- Backend: `http://localhost:8000` (Swagger at `/docs`)
- Frontend: `http://localhost:5173`

`backend/Dockerfile` uses **the project root as its build context** — `backend/app/main.py` imports `simulator/` and `amhs/` from the repo root, so it must be built from the root (`docker-compose.yml` already does this correctly). The backend image uses `backend/requirements.txt`, a slim runtime-only dependency list that excludes notebook-only packages (torch, matplotlib, jupyter, etc.).

**Worth knowing**:
- If `models/` and `data/processed/` already have joblib/CSV artifacts locally (i.e. you've run the notebooks), they're baked into the image. Without them, the container still starts fine and only the ML-dependent endpoints return 503 — same behavior as running locally without a trained model.
- The SQLite DB (`backend/semisense.db`) lives inside the container and is lost when the container is removed — fine for a portfolio demo, but would need a volume mount to persist data.
- **Verified in CI, not locally** — the local dev environment this was built in has no WSL2/Hyper-V, so `docker compose up` couldn't be run there directly. Instead, the `docker-build` job in `.github/workflows/tests.yml` runs `docker compose up --build` on GitHub Actions' Docker-native ubuntu runners on every push, and checks both the backend health endpoint (`/api/health`) and the frontend response — arguably more thorough than a single local run, since it's re-verified on every change.

## 💡 Interview talking points

> To understand real fab process flow, I worked from SECOM's actual sensor data plus published Korean-language process-monitoring papers (Seoul National University, KISTI).
> The data has heavy missingness and severe class imbalance, so I did feature selection and SMOTE-based augmentation before modeling.
> I built an Isolation Forest (unsupervised) + XGBoost (supervised) ensemble for anomaly detection — XGBoost alone reaches F1 0.228 / AUROC 0.692; the recall-first ensemble reaches F1 0.235 with 47.6% recall on real defects.
> I deliberately separated SECOM (training/evaluation) from the process simulator (real-time inference) as two independent modules, reflecting how these systems actually differ in production — a real fab's incoming sensor stream has no offline label, unlike a training set.
> I extended this into a FastAPI + React dashboard with live monitoring, and later added an AMHS module (OHT dispatch simulation, dispatch-policy comparison, predictive maintenance) and a yield-to-cost framework connecting model thresholds to a cost-based decision, to go deeper on both the logistics side and the "why does this matter to the business" side of a fab.

## 🚀 Progress checklist

- [x] Repository created, SECOM data downloaded, EDA (`notebooks/01_eda.ipynb`)
- [x] Missing-value analysis — 28 of 590 features exceed 50% missing
- [x] Class distribution — 1463 pass / 104 fail (93.36% / 6.64%)
- [x] Preprocessing (`notebooks/02_preprocessing.ipynb`) — drop >50%-missing features, median imputation, drop low-variance features, `StandardScaler`, SMOTE (train only) → `data/processed/`
- [x] Process simulator (`simulator/process_simulator.py`) — 8-process synthetic data generator with real spec ranges, ~10% anomaly rate
- [x] Anomaly detection models (`notebooks/03_modeling.ipynb`) — Isolation Forest + XGBoost ensemble, 5-fold OOF threshold tuning
- [x] FastAPI backend (`backend/`) — 11 base endpoints + 4 more added for dashboard needs, SQLite schema, curl-tested
- [x] React dashboard (`frontend/`) — 5 screens, manually tested end-to-end in browser
- [x] SHAP explainability — global/local explanations, `POST /api/ai/explain`, SHAP bars in the dashboard
- [x] pytest suite — 92 tests across backend/simulator/amhs, ML-dependent tests skip gracefully on a fresh clone
- [x] Feature selection experiment — AUROC improved (0.692→0.741) but F1 worsened (0.228→0.154); kept the baseline
- [x] LSTM Autoencoder — per-process models on simulator time series, last-timestep reconstruction error, avg F1 0.955
- [x] WM-811K wafer-map CNN — 8-class defect classification, test accuracy 0.605 / macro F1 0.664
- [x] AMHS concept write-up (`docs/AMHS.md` / `docs/AMHS.en.md`)
- [x] OHT/stocker logistics simulation (`amhs/`, `notebooks/07`) — SimPy discrete-event sim, back-pressure via resource-queue-as-buffer, 4 dispatch policies compared, vehicle-count and stocker-capacity sensitivity, predictive-maintenance feedback (+6.7% avg cycle time when vehicles fail periodically)
- [x] Transport-delay prediction (`notebooks/08`) — run-level split, R² 0.933 / delay-classification F1 0.947, real-time system load dominates static distance as a predictor
- [x] OHT vehicle predictive maintenance (`amhs/vehicle_health_simulator.py`, `notebooks/09`) — SECOM's IF+XGBoost+SHAP pipeline reapplied to vehicle sensor data
- [x] AMHS dashboard screen — live dispatch-policy comparison and vehicle-count sensitivity
- [x] AMHS 2D transport animation (`POST /api/amhs/simulate/replay`, `frontend/src/components/AmhsAnimation.jsx`) — canvas replay of OHT vehicles actually moving around the 8-station circular track (play/pause, speed, scrub), hot-lot vehicles color-coded
- [x] Predictive dispatching + predictive-maintenance feedback wired into the live simulation/dashboard (not left as notebook-only evaluation)
- [x] GitHub Actions CI — backend pytest + frontend Vitest/build + Docker build/health-check on every push/PR
- [x] Frontend tests (Vitest + React Testing Library) — 13 tests, including partial-failure UI states
- [x] Dockerized (`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`) — verified via a `docker-build` CI job (build + health check + frontend response) on every push, since the local dev environment has no WSL2/Hyper-V
- [x] Cpk/Ppk + SPC control charts (`simulator/spc.py`, `notebooks/10`) — I-MR charts, Western Electric rules, capability indices for 21 parameters, SPC detection F1 0.813
- [x] Hot lot priority dispatching (`amhs/simulation.py`) — no effect without contention (84.0s vs 83.4s), 31% faster under contention (190.5s vs 276.5s, averaged over 15 seeds) — priority only matters when there's actual resource contention
- [x] Real literature grounding for AMHS dispatch design (`docs/AMHS.md` §8) — 6 real papers cited, each mapped to what it does/doesn't correspond to in this implementation
- [x] Yield-to-cost quantification framework (`notebooks/11`) — cost-mapped confusion matrix, F1-optimal vs cost-optimal thresholds, re-inspection capacity constraint, an honest note on where the ranking is unstable at this sample size
- [x] English documentation (this file, `docs/AMHS.en.md`)
- [x] Hugging Face Space deployment prep (`Dockerfile.space`, static-file serving added to `backend/app/main.py`, verified via a `space-build` CI job that actually builds and health-checks the container) — actual deployment held back, though: this account's Docker SDK Space tier is paid-gated (only Static/Gradio are free), and per this project's zero-cost constraint, local execution (`docker compose up`) plus CI verification stand in for a live deployment instead
- [x] Root-cause label + cause/impact/fix suggestion (`simulator/diagnosis.py`) — when a process parameter goes out of spec, instantly proposes a domain-informed likely cause, downstream impact, and fix via static rules (no LLM, no cost). All 8 processes × 24 parameters × 2 directions verified mapped by a completeness test; exposed via the `diagnoses` field on `POST /api/process/simulate` and friends, shown on the dashboard
- [x] AI-based fault classifier (`simulator/fault_scenarios.py`, `notebooks/12_fault_scenario_classification.ipynb`) — XGBoost infers the cause from correlated multi-parameter patterns instead of a hardcoded rule (81-87% accuracy across 8 processes). Found the default demo data (independent random perturbation) doesn't match any trained pattern, so mostly predicts "normal" — added `POST /api/process/fault-demo` (injects the actual trained patterns, re-verified at 83.5% over 200 samples) to demonstrate what the classifier is actually good at
