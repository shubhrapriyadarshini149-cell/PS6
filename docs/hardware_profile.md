# Hardware Profile

**Recorded on:** 2026-10-03

## System Specifications
- **OS:** Windows 10
- **Processor:** Intel64 Family 6 Model 186 Stepping 3 (10 physical cores, 12 logical)
- **RAM:** 7.65 GB Total (~1 GB available at test time)
- **GPU:** None (CPU inference only)

## Raw Inference Speed (PyTorch CPU)
Measured on a dummy 720p image (1280x720):
- **YOLOv8n (Nano):** ~23.25 FPS
- **YOLOv8m (Medium):** ~4.08 FPS

## Architecture Implications
- We have no GPU and limited RAM.
- A single YOLOv8m model running at 4 FPS means we cannot process every frame on multiple cameras.
- **Shared Inference Scheduler (ADR-3) is critical.** We'll need to run inference perhaps once every 5-10 frames per camera and rely on ByteTrack (which is very fast) to handle the frames in between.
- If we run 3 cameras, they will effectively share a budget of 4 FPS for the PPE model (e.g., ~1.3 inference FPS per camera).
