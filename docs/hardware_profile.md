# Hardware Profile

**Updated on:** 2026-10-05

## System Specifications
- **OS:** Windows 11
- **Processor:** Intel64 Family 6 Model 186 Stepping 2 (8 physical cores, 12 logical)
- **RAM:** 15.64 GB Total (6.06 GB available)
- **GPU:** **NVIDIA GeForce RTX 4050 Laptop GPU** (6 GB VRAM)
- **CUDA Runtime:** Version 12.6

## Measured Inference Speed (RTX 4050 GPU vs CPU)
Tested on 720p image (1280x720):

| Model | CPU Mode (Previous) | RTX 4050 GPU (Current) | Speedup Factor |
|---|---|---|---|
| **YOLOv8n (Nano)** | ~0.90 FPS | **132.94 FPS** | **~147x faster** |
| **YOLOv8m (Medium - Primary PPE)** | ~0.31 FPS | **76.75 FPS** | **~247x faster** |

## Performance Impact
- **Real-Time Multi-Camera Streaming**: At **76.75 FPS**, the RTX 4050 GPU can easily process multiple high-resolution video streams and IP cameras simultaneously at full frame rate with virtually zero latency.
- **Buttery-Smooth Playback**: Video playback in the dashboard now runs in real time instead of stuttering.
