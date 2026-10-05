# PRD: AI Factory Safety Monitoring System (Pre-trained Model Edition)

| | |
|---|---|
| **Status** | Draft v0.1 |
| **Date** | 2026-10-03 |
| **Project** | PS06 |
| **Owner** | TBD |

> Basis: this PRD is written from the project summary shared in chat (structure of `src/`, `config/`, `rules.yaml`, `detect_video.py`). Items marked **[Assumption]** or **[Proposed]** need your confirmation. Metric targets are proposals, not measured results.

---

## 1. Summary

An edge pipeline that ingests factory video (MP4 files and RTSP cameras), detects workers, checks that they wear the PPE required for their zone, detects fire and smoke, and raises de-duplicated alerts with evidence snapshots. This revision **removes all model training** from the project. Detection relies on publicly available pre-trained weights, wrapped by a model-adapter layer and validated by a benchmark gate before any model is accepted.

## 2. Problem and goals

**Problem.** Manual monitoring of PPE compliance and early fire hazards is inconsistent and does not scale across cameras.

**Goals**
1. Flag sustained PPE violations per zone (hardhat, safety vest at minimum) with few false alarms.
2. Flag fire and smoke early, and escalate when a person is near a fire.
3. Run without any in-house training, using swappable pre-trained weights.
4. Make model choice evidence-based: a model ships only if it passes the acceptance gate in section 8.

**Non-goals**
- Training or fine-tuning models (kept only as an escalation path, see section 11, R1).
- Replacing certified fire alarms or safety systems. This is an assistive monitor.
- Face recognition or worker identification.
- Gloves, goggles, harness and fall detection in v1 (can be added later via the same adapter).

## 3. Users

| User | Need |
|---|---|
| Safety officer / supervisor | Review alerts, evidence, trends per zone |
| Plant operator | Immediate notification of fire or serious violation |
| Engineer / maintainer | Swap models, tune thresholds, read logs |

## 4. Scope

**In scope:** stream ingestion, person detection, PPE detection, fire/smoke detection, tracking, zone rules, temporal smoothing, alerting (SQLite log, snapshots, Telegram), Streamlit dashboard, model adapter, benchmark tooling.

**Out of scope for v1:** cloud multi-site management, mobile app, automatic model retraining.

## 5. Architecture decision (ADR-001): model stack

**Decision.** Two detector models plus ByteTrack, behind a model-adapter layer.

| Role | Primary (chosen) | Challenger | Rationale |
|---|---|---|---|
| PPE + person | `Hexmon/vyra-yolo-ppe-detection` (YOLOv8m, 14 classes incl. Person, Hardhat, Safety Vest, NO-* variants; dataset CC BY 4.0) | `ayushgupta7777/safetyvision-yolov8` v2 small, run at 896 px | Medium capacity should beat nano models on small, distant hardhats. It includes a Person class, so no third model is needed initially. The challenger publishes per-class metrics and an 896 px export, which helps with small objects. |
| Fire + smoke | `rabahdev/fire-smoke-yolov8n` (D-Fire; reported mAP50 0.754; class 0 smoke, 1 fire) | ProFSAM YOLO11n fire detector (FASDD subset, fire only) | Only option found that covers both fire and smoke. Its modest accuracy is acceptable only because of temporal smoothing and the benchmark gate. |
| Tracking | ByteTrack (existing) | none | Already in the codebase. |

**Design rules that follow from this decision**
1. **Positive classes drive compliance.** A hardhat or vest box must geometrically fall on the person (existing `ppe_rules.py` logic). `NO-Hardhat` and `NO-Safety Vest` are used only as *corroborating* evidence, never as the sole trigger. Published per-class numbers for the challenger show the NO-Safety Vest class is weak, so it cannot be trusted alone.
2. **Map by class name, never by index.** Fire models disagree on class order (FASDD 0=fire, D-Fire 0=smoke).
3. **Person source gate.** Use the PPE model's Person class. If person recall at distance fails the gate in section 8, add stock `yolo11n.pt` (COCO) for the person class only.
4. **Models are config, not code.** Weights path, alias map, thresholds and image size live in YAML per model.

**Alternatives considered and rejected**
- *Single stock COCO model:* cannot detect PPE.
- *Training a custom model:* excluded by project direction. Retained as the escalation path.
- *Permissively licensed detectors (e.g. RF-DETR, RT-DETR):* attractive if AGPL is a blocker, but would need fine-tuning. Verify their license terms independently before relying on this path.

**This choice is provisional.** The primary models become final only after passing section 8. If the primary fails and the challenger passes, the challenger replaces it with a config change only.

## 6. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Ingest MP4 and RTSP sources defined in `cameras.yaml`; drop stale frames when behind. | Must |
| FR-2 | Run PPE and fire/smoke inference every Nth frame (N configurable). | Must |
| FR-3 | Assign persistent track IDs to persons. | Must |
| FR-4 | Per-zone required-PPE rules from `rules.yaml`; associate PPE to person by geometry. | Must |
| FR-5 | Temporal smoothing: raise NON-COMPLIANT only when a violation persists across a configurable window. | Must |
| FR-6 | Fire/smoke alert with debounce; escalate severity when a tracked person is within a configurable distance of fire. | Must |
| FR-7 | Alert outputs: SQLite record, snapshot image, optional Telegram message; cooldown per track and per camera to prevent spam. | Must |
| FR-8 | Model adapter: load any listed model, normalize class names via alias map, fail fast with a clear error if required classes are missing. | Must |
| FR-9 | Benchmark tool: evaluate a model on the labeled eval set and on clips, producing a report (per-class precision/recall, FPS, pipeline-level alert metrics). | Must |
| FR-10 | Dashboard to browse alerts, filter by camera/zone/time, view snapshots. | Should |
| FR-11 | Model registry file recording source URL, commit hash, SHA-256, license, class list, date added. | Should |

## 7. Non-functional requirements

| ID | Requirement | Target **[Proposed]** |
|---|---|---|
| NFR-1 | Alert latency from event start to alert | under 5 s for fire; under 10 s for PPE (includes smoothing window) |
| NFR-2 | Inference throughput | at least 10 effective FPS per stream on target hardware **[Assumption: hardware TBD]** |
| NFR-3 | Reliability | stream reconnect with backoff; pipeline survives a single camera failure |
| NFR-4 | Privacy | snapshots stored locally; no video leaves the edge node unless Telegram alerts are enabled |
| NFR-5 | Reproducibility | pinned model hashes; same input yields same outputs on same model and config |
| NFR-6 | Maintainability | swap a model by editing YAML only |

## 8. Evaluation plan and acceptance gate

**Eval data.** 100–200 frames labeled from your own cameras (CVAT or Label Studio), plus 5–10 short labeled clips. Must include: crowding, far-away workers, partial occlusion, night or low light, orange or yellow clothing that resembles vests, welding glare, steam. For fire: use clips with real fire if available, and add the public D-Fire and FASDD negatives for lookalikes. This set is used for **testing only**.

**Two-level evaluation**
1. *Detector level:* per-class precision, recall, mAP50 on the eval frames; FPS on target hardware.
2. *Pipeline level:* on clips, count alert-level true/false positives and misses after tracking and smoothing.

**Acceptance gate [Proposed, adjust after baseline run]**

| Metric | Gate |
|---|---|
| PPE violation alerts: precision | at least 0.90 |
| PPE violation alerts: recall | at least 0.80 |
| Person recall (all distances in eval set) | at least 0.90 |
| Fire false alarms | at most 1 per camera per 24 h on soak test footage |
| Fire/smoke recall on labeled clips | at least 0.85 for fire, report smoke separately |
| Throughput | meets NFR-2 |

**Decision procedure:** run both candidates per role, apply the gate, choose the passing model with the best pipeline-level result; if none passes, trigger the R1 escalation.

## 9. Configuration changes

- `config/models.yaml` (new): per model entry with `weights`, `imgsz`, `conf` per class, `alias` map (e.g. `Hardhat: hardhat`, `Safety Vest: vest`, `Person: person`), `required_classes`, `license`, `sha256`.
- `config/rules.yaml`: keep zone-to-required-PPE rules; add `use_negative_classes: corroborate | ignore`.
- Remove any dependency of `detect_video.py` or `detectors.py` on `train_ppe.py` and `ppe_dataset/`.

## 10. Legal and licensing

- Nearly all candidate weights are AGPL-3.0 through Ultralytics. Internal use is generally simpler; distributing or offering the system as a network service to others may carry source-disclosure obligations. **Get this reviewed before commercial deployment.**
- Dataset licenses vary (the primary PPE model's dataset is CC BY 4.0, which requires attribution). Record attribution in the model registry.
- One fire-related candidate repository was found under a non-commercial license; avoid it if commercial use is intended.
- Not legal advice.

## 11. Risks and mitigations

| ID | Risk | Mitigation |
|---|---|---|
| R1 | No public model reaches the gate on your cameras (domain shift) | Escalation path: fine-tune on your labeled frames; this is the only scenario where training re-enters scope |
| R2 | Misassigned PPE in crowded scenes (box-containment association) | Test crowded frames in eval set; tighten head and torso region logic; tune thresholds |
| R3 | Fire false alarms from welding, lamps, sunlight | Lookalike negatives in eval set; require sustained detection; allow per-camera masks and thresholds |
| R4 | Weak NO-* classes cause bad alerts | Corroborate-only rule (section 5) |
| R5 | Community models disappear or change | Pin hash and mirror weights locally |
| R6 | Model-card claims are unverified | Gate based on your own data, not published metrics |
| R7 | AGPL obligations | Legal review (section 10) |

## 12. Milestones

| Phase | Deliverable | Exit criterion |
|---|---|---|
| 0. Cleanup | Training artifacts archived to a branch; imports verified | App runs without training files |
| 1. Eval set | Labeled frames and clips; labeling guide | Reviewed and frozen |
| 2. Adapter | `models.yaml`, alias mapping, class validation, registry | Both candidate models load and produce normalized classes |
| 3. Benchmark | Benchmark tool and first report | Report generated for all candidates |
| 4. Tune and select | Thresholds, image size, smoothing window tuned; models chosen | Acceptance gate passed or R1 triggered |
| 5. Harden | Reconnect logic, cooldowns, soak test, dashboard polish | 24 h soak test passes |
| 6. Release | Docs, runbook, model registry finalized | Sign-off |

## 13. Open questions

1. Target hardware (CPU only, NVIDIA GPU, Jetson)? This drives model size and imgsz.
2. Number of cameras and stream resolutions?
3. Which PPE items are mandatory in each zone beyond hardhat and vest?
4. Is deployment commercial or internal (licensing impact)?
5. Who receives alerts, and what response time is expected?
6. Can you provide representative footage, including real fire or smoke samples?

## 14. Success metrics

- Pipeline-level precision and recall meet the section 8 gate.
- Fire false alarms per camera per day stay within the gate over soak testing.
- Time to swap a model (config change plus benchmark run): under 1 hour.
- Zero training code or dataset needed to run or deploy.
