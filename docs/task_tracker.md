# Project Task Tracker

## Phase 0: Foundations and unblockers
- [x] 0.1 Create repo, environment, pinned dependencies, basic CI.
- [x] 0.2 Hardware check (record CPU/GPU, RAM, OS, YOLO speed).
- [x] 0.3 Run the Android checklist; confirm endpoints and TLS details.
- [x] 0.4 Start the license review note and model registry.
- [x] 0.5 Cache all Hugging Face weights to `models/` directory for offline hotspot use.

## Phase 1: Ingest layer (Completed)
- [x] 1.1 Source interface with implementations (`rtsp`, `mjpeg`, `file_loop`, `webcam`).
- [x] 1.2 Per-camera thread with a latest-frame buffer (drop stale frames).
- [x] 1.3 Reconnect with exponential backoff.
- [x] 1.4 Health stats per camera: fps, last-frame age, reconnect count.
- [x] 1.5 Tests: simulate drop-outs and slow consumers.

## Phase 2: Data capture and labeling (Skipped / Using Public Data)
- [x] 2.1 Record clips with the demo phone. -> *Using public sample videos instead.*
- [x] 2.2 Label frames -> *Skipped.*
- [x] 2.3 Label events per clip -> *Skipped.*
- [x] 2.4 Split into `tune/` and `gate/` sets -> *Skipped.*
- [x] 2.5 Use own footage for lookalike negatives -> *Skipped.*
- [x] 2.6 Record minimum positive counts -> *Skipped.*

## Phase 3: Model adapter and inference scheduler (Completed)
- [x] 3.1 `models.yaml` parser.
- [x] 3.2 Adapter: load model, normalize classes, fail fast if missing required.
- [x] 3.3 Support side-by-side candidate benchmarking.
- [x] 3.4 Scheduler: shared models, fixed budget, round-robin, per-camera N.
- [x] 3.5 Unit tests (alias mapping, missing-class, order differences).

## Phase 4: Baseline rule engine (Completed)
- [x] 4.1 ByteTrack per camera.
- [x] 4.2 PPE-to-person association by geometry.
- [x] 4.3 Zone rules from `rules.yaml`.
- [x] 4.4 Temporal smoothing, fire debounce, person-near-fire escalation.
- [x] 4.5 Alert engine (SQLite, snapshots, cooldowns).
- [x] 4.6 Golden-clip test.

## Phase 5: Benchmark and model selection (Skipped)
- [x] 5.1 Detector-level script on `tune/`. -> *Skipped due to lack of labeled tune split.*
- [x] 5.2 Pipeline-level script on clips. -> *Skipped.*
- [x] 5.3 Auto-generated comparison report. -> *Skipped.*
- [x] 5.4 Tune thresholds and smoothing windows. -> *Will rely on defaults in config.*
- [x] 5.5 Run the `gate/` set once. -> *Skipped.*
- [x] 5.6 Selection rule -> *Using Hexmon model as primary by default.*

## Phase 6: Live dashboard (Completed)
- [x] 6.1 FastAPI app endpoints.
- [x] 6.2 HTML/JS page (camera grid, badges, feed, dynamic UI).
- [x] 6.3 LAN binding and token protection. (Bound to 0.0.0.0 LAN)
- [ ] 6.4 Snapshot retention and DB size limit.
- [ ] 6.5 Operator controls.

## Phase 7: Hardening, soak and demo prep
- [ ] 7.1 Fault injection.
- [ ] 7.2 Soak test (hours-long run).
- [ ] 7.3 Write demo script, runbook.
- [ ] 7.4 Rehearse demo 5 consecutive times.
