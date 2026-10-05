document.addEventListener("DOMContentLoaded", () => {
    const addCameraBtn = document.getElementById("add-camera-btn");
    const modal = document.getElementById("camera-modal");
    const closeBtn = document.querySelector(".close-btn");
    const cancelBtn = document.getElementById("modal-cancel-btn");
    const deleteBtn = document.getElementById("modal-delete-btn");
    const form = document.getElementById("add-camera-form");
    const grid = document.getElementById("camera-grid");

    const modalTitle = document.getElementById("modal-title");
    const modalSubmitBtn = document.getElementById("modal-submit-btn");
    const camOriginalName = document.getElementById("cam-original-name");
    const camName = document.getElementById("cam-name");
    const camType = document.getElementById("cam-type");
    const camUrl = document.getElementById("cam-url");
    const camUser = document.getElementById("cam-user");
    const camPass = document.getElementById("cam-pass");
    const camTls = document.getElementById("cam-tls");

    // Cache current cameras by name
    const currentCameras = new Map();

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function sanitizeId(str) {
        return "cam-card-" + String(str).replace(/[^a-zA-Z0-9_-]/g, "_");
    }

    // Dynamic placeholder and label helper based on type
    camType.addEventListener("change", () => {
        const urlLabel = camUrl.previousElementSibling;
        if (camType.value === "file_loop") {
            if (urlLabel) urlLabel.textContent = "Video File Path (MP4 file)";
            camUrl.placeholder = "eval/data/clips/sample_workers.mp4";
        } else if (camType.value === "webcam") {
            if (urlLabel) urlLabel.textContent = "Webcam Device Index";
            camUrl.placeholder = "0";
        } else {
            if (urlLabel) urlLabel.textContent = "URL / Source (e.g. https:// or rtsp://)";
            camUrl.placeholder = "https://10.79.84.100:4444/video/mjpeg";
        }
    });

    // Modal display functions
    function openAddModal() {
        modalTitle.textContent = "Add New Camera";
        modalSubmitBtn.textContent = "Connect Camera";
        deleteBtn.style.display = "none";
        camOriginalName.value = "";
        form.reset();
        camType.value = "mjpeg";
        camTls.checked = false;
        modal.style.display = "flex";
        camName.focus();
    }

    function openEditModal(name) {
        const cam = currentCameras.get(name);
        if (!cam) return;

        modalTitle.textContent = `Edit Camera: ${cam.name}`;
        modalSubmitBtn.textContent = "Save Changes";
        deleteBtn.style.display = "inline-block";
        camOriginalName.value = cam.name;
        camName.value = cam.name;
        camType.value = cam.type || "mjpeg";
        camUrl.value = cam.url || "";
        camUser.value = cam.username || "";
        camPass.value = ""; // Leave blank so existing password is kept
        camTls.checked = Boolean(cam.verify_tls);

        modal.style.display = "flex";
        camName.focus();
    }

    function closeModal() {
        modal.style.display = "none";
    }

    // Modal Event Listeners
    addCameraBtn.onclick = openAddModal;
    closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;
    window.onclick = (e) => {
        if (e.target === modal) closeModal();
    };

    // Delete Camera
    if (deleteBtn) {
        deleteBtn.onclick = async () => {
            const targetName = camOriginalName.value.trim() || camName.value.trim();
            if (!targetName) return;

            if (!confirm(`Are you sure you want to remove "${targetName}"?`)) {
                return;
            }

            try {
                const res = await fetch(`/api/cameras/${encodeURIComponent(targetName)}`, {
                    method: "DELETE"
                });
                const data = await res.json();
                if (data.status === "success") {
                    closeModal();
                    await refreshCameras();
                } else {
                    alert(data.message || "Failed to delete camera");
                }
            } catch (err) {
                console.error("Error deleting camera:", err);
                alert("Error deleting camera");
            }
        };
    }

    // Form Submit (Add or Edit)
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const originalName = camOriginalName.value.trim();
        const payload = {
            name: camName.value.trim(),
            type: camType.value,
            url: camUrl.value.trim(),
            username: camUser.value.trim(),
            password: camPass.value,
            verify_tls: camTls.checked,
            original_name: originalName
        };

        try {
            modalSubmitBtn.disabled = true;
            modalSubmitBtn.textContent = "Connecting...";

            const url = originalName ? `/api/cameras/${encodeURIComponent(originalName)}` : "/api/cameras";
            const method = originalName ? "PUT" : "POST";

            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            modalSubmitBtn.disabled = false;
            modalSubmitBtn.textContent = originalName ? "Save Changes" : "Connect Camera";

            if (data.status === "success") {
                closeModal();
                form.reset();

                // Rapid refresh sequence: instantly show card and poll until video stream is live
                await refreshCameras();
                setTimeout(refreshCameras, 500);
                setTimeout(refreshCameras, 1500);
                setTimeout(refreshCameras, 3000);
            } else {
                alert(data.message || "Failed to save camera settings");
            }
        } catch (err) {
            modalSubmitBtn.disabled = false;
            modalSubmitBtn.textContent = originalName ? "Save Changes" : "Connect Camera";
            console.error("Error saving camera:", err);
            alert("Error saving camera settings");
        }
    });

    async function refreshCameras() {
        try {
            const res = await fetch("/api/cameras");
            const data = await res.json();
            renderGrid(data.cameras || []);
        } catch (err) {
            console.error("Failed to fetch cameras:", err);
        }
    }

    function renderGrid(cameras) {
        const counter = document.getElementById("stream-counter");
        if (counter) {
            const count = (cameras || []).length;
            counter.textContent = `${count} Active Stream${count === 1 ? '' : 's'}`;
        }

        if (!cameras || cameras.length === 0) {
            grid.innerHTML = '<div style="color:var(--text-muted); width: 100%; padding: 20px; font-size: 0.85rem;">No streams active. Click "+ Add" on any source in the left sidebar.</div>';
            currentCameras.clear();
            renderAvailableSources();
            return;
        }

        // Remove placeholder if present
        const placeholder = grid.querySelector('div[style*="No cameras active"]');
        if (placeholder) placeholder.remove();

        const activeNames = new Set(cameras.map(c => c.name));

        // Remove stale cards
        for (const [name] of currentCameras) {
            if (!activeNames.has(name)) {
                const card = document.getElementById(sanitizeId(name));
                if (card) card.remove();
                currentCameras.delete(name);
            }
        }

        // Add or smoothly update each camera
        cameras.forEach(cam => {
            currentCameras.set(cam.name, cam);
            const cardId = sanitizeId(cam.name);
            let card = document.getElementById(cardId);

            const isAlive = Boolean(cam.is_alive);
            const statusClass = isAlive ? "ok" : (cam.reconnect_count > 0 ? "offline" : "warning");
            const statusText = isAlive ? "LIVE" : (cam.reconnect_count > 0 ? "OFFLINE" : "CONNECTING");
            const metaInfo = `${escapeHtml(cam.type || "stream")} • ${cam.fps || 0} FPS`;
            const streamUrl = `/stream/${encodeURIComponent(cam.name)}`;

            if (card) {
                // Update badge and meta info in-place
                const badge = card.querySelector(".badge");
                if (badge) {
                    badge.className = `badge ${statusClass}`;
                    badge.textContent = statusText;
                }

                const metaSpan = card.querySelector(".camera-meta-info");
                if (metaSpan) {
                    metaSpan.textContent = metaInfo;
                }

                const overlay = card.querySelector(".stream-overlay");
                const img = card.querySelector(".mjpeg-stream");

                if (overlay) {
                    if (isAlive) {
                        overlay.style.display = "none";
                    } else {
                        overlay.style.display = "flex";
                        const overlayMsg = overlay.querySelector(".overlay-msg");
                        if (overlayMsg) {
                            overlayMsg.textContent = cam.reconnect_count > 0 ? "Reconnecting stream..." : "Connecting to camera...";
                        }
                    }
                }

                // If image was never mounted or had error, re-attach stream src
                if (img && (!img.src || img.src.includes("data:,") || !img.src.includes(encodeURIComponent(cam.name)))) {
                    img.src = streamUrl;
                }
            } else {
                // Create new card with active stream img AND overlay
                card = document.createElement("div");
                card.id = cardId;
                card.className = "camera-card glass-panel";

                card.innerHTML = `
                    <div class="camera-header">
                        <div class="camera-title-wrap">
                            <h3>${escapeHtml(cam.name)}</h3>
                            <span class="camera-meta-info">${metaInfo}</span>
                        </div>
                        <div class="camera-header-actions">
                            <span class="badge ${statusClass}">${statusText}</span>
                            <button class="btn-icon edit-cam-btn" title="Edit Camera Settings" type="button">
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M12 20h9"></path>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="video-container">
                        <img src="${streamUrl}" class="mjpeg-stream" alt="${escapeHtml(cam.name)} stream" />
                        <div class="stream-overlay" style="${isAlive ? 'display:none;' : 'display:flex;'}">
                            <div class="stream-spinner"></div>
                            <span class="overlay-msg">${cam.reconnect_count > 0 ? 'Reconnecting stream...' : 'Connecting to camera...'}</span>
                        </div>
                    </div>
                `;

                // Auto-hide overlay once first frame is rendered
                const img = card.querySelector(".mjpeg-stream");
                const overlay = card.querySelector(".stream-overlay");
                if (img && overlay) {
                    img.onload = () => {
                        overlay.style.display = "none";
                    };
                }

                // Attach edit button listener
                const editBtn = card.querySelector(".edit-cam-btn");
                if (editBtn) {
                    editBtn.onclick = () => openEditModal(cam.name);
                }

                grid.appendChild(card);
            }
        });
        renderAvailableSources();
    }

    // Available Sources State & Methods
    let cachedSources = { videos: [], cameras: [] };

    async function fetchAvailableSources(isManual = false) {
        try {
            const res = await fetch("/api/sources/available");
            const data = await res.json();
            cachedSources = {
                videos: data.videos || [],
                cameras: data.cameras || []
            };
            renderAvailableSources();
        } catch (err) {
            console.warn("Failed to fetch available sources:", err);
        }
    }

    function isSourceActive(source) {
        for (const [name, cam] of currentCameras) {
            if (name.toLowerCase() === source.name.toLowerCase()) return true;
            if (source.path && (cam.url === source.path || String(cam.url).endsWith(source.filename))) return true;
            if (source.url && (cam.url === source.url || (String(source.url) === "0" && String(cam.url) === "0"))) return true;
        }
        return false;
    }

    function renderAvailableSources() {
        const videoContainer = document.getElementById("video-sources-pills");
        const cameraContainer = document.getElementById("camera-sources-pills");

        // 1. Render Video List in Sidebar
        if (videoContainer) {
            if (!cachedSources.videos || cachedSources.videos.length === 0) {
                videoContainer.innerHTML = '<span class="loading-sources">No clips in eval/data/clips/</span>';
            } else {
                videoContainer.innerHTML = "";
                cachedSources.videos.forEach(video => {
                    const active = isSourceActive(video);
                    const item = document.createElement("div");
                    item.className = `sidebar-source-item ${active ? 'active' : ''}`;
                    item.title = active ? `${video.name} is streaming` : `Click to add ${video.name}`;

                    item.innerHTML = `
                        <div class="source-left">
                            <span class="source-icon">🎬</span>
                            <div class="source-info">
                                <span class="source-title">${escapeHtml(video.name)}</span>
                                <span class="source-subtitle">${video.size_mb} MB</span>
                            </div>
                        </div>
                        <span class="source-status-btn ${active ? 'active' : ''}">${active ? 'Active ✓' : '+ Add'}</span>
                    `;

                    if (!active) {
                        item.onclick = () => {
                            quickAddSource({
                                name: video.name,
                                type: "file_loop",
                                url: video.path,
                                username: "",
                                password: "",
                                verify_tls: false
                            }, item, "Adding...");
                        };
                    }
                    videoContainer.appendChild(item);
                });
            }
        }

        // 2. Render Camera List in Sidebar
        if (cameraContainer) {
            if (!cachedSources.cameras || cachedSources.cameras.length === 0) {
                cameraContainer.innerHTML = '<span class="loading-sources">Scanning devices...</span>';
            } else {
                cameraContainer.innerHTML = "";
                cachedSources.cameras.forEach(cam => {
                    const active = isSourceActive(cam);
                    const isWebcam = cam.type === "webcam";
                    const isReachable = Boolean(cam.reachable);
                    const item = document.createElement("div");
                    item.className = `sidebar-source-item ${active ? 'active' : ''} ${!isReachable && !isWebcam ? 'offline' : ''}`;
                    item.title = active 
                        ? `${cam.name} is streaming` 
                        : (isReachable ? `Click to connect ${cam.name}` : `${cam.name} (Standby). Click to connect`);

                    const icon = isWebcam ? '💻' : '📱';
                    const subtitle = isWebcam ? 'Device 0' : (isReachable ? 'Online' : 'Standby');

                    item.innerHTML = `
                        <div class="source-left">
                            <span class="source-icon">${icon}</span>
                            <div class="source-info">
                                <span class="source-title">${escapeHtml(cam.name)}</span>
                                <span class="source-subtitle">${subtitle}</span>
                            </div>
                        </div>
                        <span class="source-status-btn ${active ? 'active' : ''}">${active ? 'Active ✓' : '+ Add'}</span>
                    `;

                    if (!active) {
                        item.onclick = () => {
                            quickAddSource({
                                name: cam.name,
                                type: cam.type,
                                url: cam.url,
                                username: cam.username || "",
                                password: cam.password || "",
                                verify_tls: Boolean(cam.verify_tls)
                            }, item, "Connecting...");
                        };
                    }
                    cameraContainer.appendChild(item);
                });
            }
        }
    }

    async function quickAddSource(payload, itemElement, loadingText = "Adding...") {
        const btn = itemElement.querySelector(".source-status-btn");
        const originalText = btn ? btn.textContent : "+ Add";
        if (btn) btn.textContent = loadingText;
        itemElement.style.pointerEvents = "none";

        try {
            const res = await fetch("/api/cameras", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === "success") {
                await refreshCameras();
                setTimeout(refreshCameras, 600);
                setTimeout(refreshCameras, 1800);
            } else {
                alert(data.message || "Failed to add source");
                if (btn) btn.textContent = originalText;
                itemElement.style.pointerEvents = "auto";
            }
        } catch (err) {
            console.error("Error adding source:", err);
            alert("Error adding source");
            if (btn) btn.textContent = originalText;
            itemElement.style.pointerEvents = "auto";
        }
    }

    async function checkSystemHardware() {
        const gpuBadge = document.getElementById("gpu-status-badge");
        const gpuText = document.getElementById("gpu-name-text");
        if (!gpuBadge || !gpuText) return;

        try {
            const res = await fetch("/api/system");
            const data = await res.json();

            if (data.cuda_available) {
                gpuBadge.className = "badge ok";
                gpuBadge.textContent = "GPU (CUDA)";
                gpuText.textContent = data.device_name || "NVIDIA Active";
                gpuText.title = `${data.device_name} (Using ${data.device})`;
            } else {
                gpuBadge.className = "badge warning";
                gpuBadge.textContent = "CPU MODE";
                gpuText.textContent = data.physical_gpu ? `${data.physical_gpu}` : "Running on CPU";
                gpuText.title = "PyTorch is currently executing on CPU.";
            }
        } catch (err) {
            console.warn("Could not query /api/system:", err);
        }
    }

    function formatTimeAgo(timestampStr) {
        if (!timestampStr) return "Just now";
        try {
            const date = new Date(timestampStr.replace(" ", "T") + "Z");
            const diffSeconds = Math.max(0, Math.floor((Date.now() - date) / 1000));
            if (diffSeconds < 5) return "Just now";
            if (diffSeconds < 60) return `${diffSeconds}s ago`;
            const diffMinutes = Math.floor(diffSeconds / 60);
            if (diffMinutes < 60) return `${diffMinutes}m ago`;
            const diffHours = Math.floor(diffMinutes / 60);
            return `${diffHours}h ago`;
        } catch (e) {
            return timestampStr;
        }
    }

    async function fetchAlerts() {
        try {
            const res = await fetch("/api/alerts");
            const data = await res.json();
            renderAlerts(data.alerts || []);
        } catch (err) {
            console.warn("Failed to fetch alerts:", err);
        }
    }

    function renderAlerts(alerts) {
        const alertList = document.getElementById("alert-list");
        const countBadge = document.getElementById("alerts-count");
        if (!alertList) return;

        if (countBadge) countBadge.textContent = alerts.length;

        if (!alerts || alerts.length === 0) {
            alertList.innerHTML = '<div class="no-alerts-placeholder">Monitoring active... No violations.</div>';
            return;
        }

        alertList.innerHTML = "";
        alerts.forEach(a => {
            const isDanger = a.alert_type === "fire" || a.alert_type === "smoke";
            const itemClass = isDanger ? "danger" : "warning";
            const icon = isDanger ? "🔥" : "⚠️";
            const title = isDanger ? `${a.alert_type.toUpperCase()} HAZARD DETECTED` : (a.details || "PPE Violation");
            const timeAgo = formatTimeAgo(a.timestamp);

            const card = document.createElement("div");
            card.className = `alert-item ${itemClass}`;

            const thumbHtml = a.snapshot_url
                ? `<a href="${a.snapshot_url}" target="_blank" class="snapshot-thumb-link" title="Click to view full snapshot evidence">
                       <img src="${a.snapshot_url}" class="snapshot-thumb" alt="Evidence" onerror="this.style.display='none';"/>
                   </a>`
                : "";

            card.innerHTML = `
                <div class="alert-icon">${icon}</div>
                <div class="alert-details">
                    <strong>${escapeHtml(title)}</strong>
                    <span>${escapeHtml(a.camera)} • Track #${escapeHtml(a.track_id)} • ${timeAgo}</span>
                </div>
                ${thumbHtml}
            `;
            alertList.appendChild(card);
        });
    }

    // Safety Summary & View Switching Logic
    const viewMonitors = document.getElementById("view-monitors");
    const viewSummary = document.getElementById("view-summary");
    const navSummaryBtn = document.getElementById("nav-summary-btn");
    const navLiveMonitorsBtn = document.getElementById("nav-live-monitors");
    const summaryBackBtn = document.getElementById("summary-back-monitors-btn");
    const openSummaryBtn = document.getElementById("open-summary-modal-btn");
    const summaryModal = document.getElementById("summary-modal");
    const closeSummaryModalBtn = document.getElementById("close-summary-modal");
    const closeSummaryBtn = document.getElementById("close-summary-btn");
    const clearAlertsBtn = document.getElementById("clear-alerts-btn");
    const pageClearAlertsBtn = document.getElementById("summary-page-clear-btn");
    const exportSummaryBtn = document.getElementById("summary-export-btn");

    function switchToMonitorsView() {
        if (viewMonitors) {
            viewMonitors.classList.add("active");
            viewMonitors.style.display = "flex";
            viewMonitors.style.flexDirection = "column";
        }
        if (viewSummary) {
            viewSummary.classList.remove("active");
            viewSummary.style.display = "none";
        }
        if (navLiveMonitorsBtn) navLiveMonitorsBtn.classList.add("active");
        if (navSummaryBtn) navSummaryBtn.classList.remove("active");
        if (summaryModal) summaryModal.style.display = "none";
    }

    function switchToSummaryView() {
        if (viewMonitors) {
            viewMonitors.classList.remove("active");
            viewMonitors.style.display = "none";
        }
        if (viewSummary) {
            viewSummary.classList.add("active");
            viewSummary.style.display = "flex";
            viewSummary.style.flexDirection = "column";
        }
        if (navSummaryBtn) navSummaryBtn.classList.add("active");
        if (navLiveMonitorsBtn) navLiveMonitorsBtn.classList.remove("active");
        if (summaryModal) summaryModal.style.display = "none";
        fetchSummary();
    }

    if (navLiveMonitorsBtn) {
        navLiveMonitorsBtn.onclick = (e) => {
            e.preventDefault();
            switchToMonitorsView();
        };
    }

    if (navSummaryBtn) {
        navSummaryBtn.onclick = (e) => {
            e.preventDefault();
            switchToSummaryView();
        };
    }

    if (summaryBackBtn) {
        summaryBackBtn.onclick = () => {
            switchToMonitorsView();
        };
    }

    if (openSummaryBtn) {
        openSummaryBtn.onclick = () => {
            switchToSummaryView();
        };
    }

    if (closeSummaryModalBtn) closeSummaryModalBtn.onclick = () => { if (summaryModal) summaryModal.style.display = "none"; };
    if (closeSummaryBtn) closeSummaryBtn.onclick = () => { if (summaryModal) summaryModal.style.display = "none"; };

    window.addEventListener("click", (e) => {
        if (e.target === summaryModal) {
            summaryModal.style.display = "none";
        }
    });

    async function handleClearLogs() {
        if (!confirm("Are you sure you want to clear all recorded safety incident logs?")) return;
        try {
            const res = await fetch("/api/alerts/clear", { method: "POST" });
            const data = await res.json();
            if (data.status === "success") {
                await fetchAlerts();
                await fetchSummary();
            }
        } catch (err) {
            console.error("Failed to clear alerts:", err);
        }
    }

    if (clearAlertsBtn) clearAlertsBtn.onclick = handleClearLogs;
    if (pageClearAlertsBtn) pageClearAlertsBtn.onclick = handleClearLogs;

    // Export Summary Report as CSV
    let lastSummaryData = null;
    if (exportSummaryBtn) {
        exportSummaryBtn.onclick = () => {
            if (!lastSummaryData) {
                alert("Summary data is still loading. Please wait a moment.");
                return;
            }
            const dateStr = new Date().toISOString().replace(/[:.]/g, "-");
            let csv = "Safety & Compliance Incident Summary Report\r\n";
            csv += `Generated At,${new Date().toLocaleString()}\r\n`;
            csv += `Compliance Rate,${lastSummaryData.compliance_rate}%\r\n`;
            csv += `Active Streams,${lastSummaryData.active_streams}\r\n`;
            csv += `Workers Tracked,${lastSummaryData.workers_tracked}\r\n`;
            csv += `Active Violations,${lastSummaryData.active_violations}\r\n`;
            csv += `Total Incidents Today,${lastSummaryData.total_alerts}\r\n`;
            csv += `Hazard Status,${lastSummaryData.hazard_status}\r\n\r\n`;

            csv += "Incidents By Camera\r\nCamera,Count\r\n";
            for (const [cam, count] of Object.entries(lastSummaryData.by_camera || {})) {
                csv += `"${cam}",${count}\r\n`;
            }

            csv += "\r\nIncidents By Category\r\nCategory,Count\r\n";
            for (const [cat, count] of Object.entries(lastSummaryData.by_type || {})) {
                csv += `"${cat}",${count}\r\n`;
            }

            csv += "\r\nRecent Incident Activity Log\r\nID,Time,Camera,Event,Track ID\r\n";
            for (const item of (lastSummaryData.recent_alerts || [])) {
                csv += `${item.id},"${item.timestamp}","${item.camera}","${item.details || item.alert_type}",#${item.track_id}\r\n`;
            }

            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `Safety_Summary_Report_${dateStr}.csv`;
            link.click();
        };
    }

    async function fetchSummary() {
        try {
            const res = await fetch("/api/summary");
            const data = await res.json();
            lastSummaryData = data;
            renderSummary(data);
        } catch (err) {
            console.warn("Failed to fetch safety summary:", err);
        }
    }

    function renderSummary(data) {
        if (!data) return;

        // 1. Update Ribbon KPIs (on Live Monitors page)
        const ribbonComp = document.getElementById("summary-compliance");
        const ribbonWorkers = document.getElementById("summary-workers");
        const ribbonViols = document.getElementById("summary-violations");
        const ribbonHazards = document.getElementById("summary-hazards");
        const ribbonAlerts = document.getElementById("summary-total-alerts");

        if (ribbonComp) {
            ribbonComp.textContent = `${data.compliance_rate}%`;
            ribbonComp.className = `kpi-val ${data.compliance_rate >= 90 ? 'ok' : 'alert'}`;
        }
        if (ribbonWorkers) ribbonWorkers.textContent = `${data.workers_tracked} Tracked`;
        if (ribbonViols) {
            ribbonViols.textContent = `${data.active_violations} Active`;
            ribbonViols.className = `kpi-val ${data.active_violations > 0 ? 'alert' : 'ok'}`;
        }
        if (ribbonHazards) ribbonHazards.textContent = data.hazard_status;
        if (ribbonAlerts) ribbonAlerts.textContent = data.total_alerts;

        // 2. Update Dedicated Safety Summary Area (Page View)
        const pageComp = document.getElementById("page-summary-compliance");
        const pageCompBadge = document.getElementById("page-compliance-badge");
        const pageCompBar = document.getElementById("page-compliance-bar");
        const pageCompFooter = document.getElementById("page-compliance-footer");

        const pageStreams = document.getElementById("page-summary-streams");
        const pageStreamsFooter = document.getElementById("page-streams-footer");
        const pageWorkers = document.getElementById("page-summary-workers");
        const pageWorkersFooter = document.getElementById("page-workers-footer");
        const pageViols = document.getElementById("page-summary-violations");
        const pageTotalAlerts = document.getElementById("page-summary-total-alerts");
        const pageRecent1h = document.getElementById("page-summary-recent-1h");
        const pageHazards = document.getElementById("page-summary-hazards");

        if (pageComp) pageComp.textContent = `${data.compliance_rate}%`;
        if (pageCompBadge) {
            pageCompBadge.textContent = data.compliance_rate >= 90 ? "Safe" : "Attention Required";
            pageCompBadge.className = `badge ${data.compliance_rate >= 90 ? 'ok' : 'warning'}`;
        }
        if (pageCompBar) {
            pageCompBar.style.width = `${Math.min(100, Math.max(5, data.compliance_rate))}%`;
            pageCompBar.style.background = data.compliance_rate >= 90 ? '#238636' : '#da3633';
        }
        if (pageCompFooter) {
            const safeCount = data.workers_compliant || 0;
            pageCompFooter.textContent = `Target: >95% • ${safeCount} of ${data.workers_tracked} personnel compliant`;
        }

        if (pageStreams) pageStreams.textContent = `${data.active_streams} Active`;
        if (pageStreamsFooter) pageStreamsFooter.textContent = `${data.active_streams} connected CCTV / IP feeds`;

        if (pageWorkers) pageWorkers.textContent = `${data.workers_tracked}`;
        if (pageWorkersFooter) {
            pageWorkersFooter.textContent = `${data.workers_compliant || 0} compliant • ${data.active_violations} violations`;
        }

        if (pageViols) {
            pageViols.textContent = `${data.active_violations}`;
            pageViols.style.color = data.active_violations > 0 ? '#f87171' : 'var(--text-primary)';
        }

        if (pageTotalAlerts) pageTotalAlerts.textContent = `${data.total_alerts}`;
        if (pageRecent1h) pageRecent1h.textContent = `${data.recent_1h} incident${data.recent_1h === 1 ? '' : 's'} in last hour`;
        if (pageHazards) pageHazards.textContent = data.hazard_status;

        // Render Page Tables: Camera Breakdown
        const pageCamTable = document.querySelector("#page-summary-camera-table tbody");
        const cameraEntries = Object.entries(data.by_camera || {});
        const summaryCamCount = document.getElementById("summary-camera-count");
        if (summaryCamCount) summaryCamCount.textContent = `${cameraEntries.length} cameras`;

        if (pageCamTable) {
            if (cameraEntries.length === 0) {
                pageCamTable.innerHTML = '<tr><td colspan="3" class="text-muted">No camera violations recorded</td></tr>';
            } else {
                const maxCount = Math.max(1, ...cameraEntries.map(([, c]) => c));
                pageCamTable.innerHTML = cameraEntries
                    .map(([cam, count]) => {
                        const pct = Math.round((count / maxCount) * 100);
                        return `
                            <tr>
                                <td><strong>${escapeHtml(cam)}</strong></td>
                                <td>
                                    <span>${count}</span>
                                    <div class="cam-progress-wrap"><div class="cam-progress-fill" style="width:${pct}%;"></div></div>
                                </td>
                                <td><span class="badge ${count > 5 ? 'danger' : 'warning'}">${count > 5 ? 'High Risk' : 'Monitored'}</span></td>
                            </tr>
                        `;
                    })
                    .join("");
            }
        }

        // Render Page Tables: Category Breakdown
        const pageCatTable = document.querySelector("#page-summary-category-table tbody");
        const categoryEntries = Object.entries(data.by_type || {});
        const summaryCatCount = document.getElementById("summary-category-count");
        if (summaryCatCount) summaryCatCount.textContent = `${categoryEntries.length} categories`;

        if (pageCatTable) {
            if (categoryEntries.length === 0) {
                pageCatTable.innerHTML = '<tr><td colspan="3" class="text-muted">No category incidents recorded</td></tr>';
            } else {
                pageCatTable.innerHTML = categoryEntries
                    .map(([cat, count]) => {
                        const label = cat === "ppe_violation" ? "PPE Breach (Hardhat / Vest)" :
                                      cat === "cellphone" ? "Mobile Phone Distraction" :
                                      cat === "intruder" ? "Restricted Zone Entry" :
                                      cat.replace(/_/g, " ").toUpperCase();
                        const isSevere = cat.includes("hazard") || cat.includes("fire") || cat.includes("smoke");
                        return `
                            <tr>
                                <td><strong>${escapeHtml(label)}</strong></td>
                                <td><span class="badge ${isSevere ? 'danger' : 'warning'}">${count}</span></td>
                                <td><span class="badge ${isSevere ? 'danger' : 'ok'}">${isSevere ? 'CRITICAL' : 'MODERATE'}</span></td>
                            </tr>
                        `;
                    })
                    .join("");
            }
        }

        // Render Page Tables: Recent Incident Activity Log with Proof Thumbnails
        const pageLogTable = document.getElementById("page-summary-log-tbody");
        if (pageLogTable) {
            const recent = data.recent_alerts || [];
            if (recent.length === 0) {
                pageLogTable.innerHTML = '<tr><td colspan="5" class="text-muted text-center" style="padding: 30px;">No incidents recorded in the database yet.</td></tr>';
            } else {
                pageLogTable.innerHTML = recent
                    .map(item => {
                        const thumb = item.snapshot_url 
                            ? `<a href="${item.snapshot_url}" target="_blank" title="View full resolution proof photo"><img src="${item.snapshot_url}" class="table-proof-thumb" alt="Proof" /></a>` 
                            : `<span class="text-muted">-</span>`;
                        const timeStr = item.timestamp ? item.timestamp.split(" ")[1] || item.timestamp : "";
                        return `
                            <tr>
                                <td>${thumb}</td>
                                <td><span style="font-family: monospace; font-size: 0.72rem;">${escapeHtml(timeStr)}</span></td>
                                <td><strong>${escapeHtml(item.camera)}</strong></td>
                                <td><span style="color: #f87171;">${escapeHtml(item.details || item.alert_type)}</span></td>
                                <td><span class="badge offline">#${escapeHtml(String(item.track_id))}</span></td>
                            </tr>
                        `;
                    })
                    .join("");
            }
        }

        // 3. Update Modal Details if modal is used
        const modalComp = document.getElementById("modal-compliance-rate");
        const modalStreams = document.getElementById("modal-active-streams");
        const modalIncidents = document.getElementById("modal-total-incidents");
        const modalHazard = document.getElementById("modal-hazard-level");
        const modalRecent1h = document.getElementById("modal-recent-1h");
        const modalStreamsDetail = document.getElementById("modal-streams-detail");

        if (modalComp) {
            modalComp.textContent = `${data.compliance_rate}%`;
            modalComp.style.color = data.compliance_rate >= 90 ? '#4ade80' : '#f87171';
        }
        if (modalStreams) modalStreams.textContent = data.active_streams;
        if (modalStreamsDetail) modalStreamsDetail.textContent = `${data.workers_tracked} active worker${data.workers_tracked === 1 ? '' : 's'}`;
        if (modalIncidents) modalIncidents.textContent = data.total_alerts;
        if (modalRecent1h) modalRecent1h.textContent = `${data.recent_1h} in last hour`;
        if (modalHazard) modalHazard.textContent = data.hazard_status;
    }

    // Rescan button listener
    const rescanBtn = document.getElementById("rescan-sources-btn");
    if (rescanBtn) {
        rescanBtn.onclick = async () => {
            rescanBtn.classList.add("scanning");
            await fetchAvailableSources(true);
            setTimeout(() => rescanBtn.classList.remove("scanning"), 400);
        };
    }

    // Initial load and periodic refresh
    refreshCameras();
    fetchAvailableSources();
    checkSystemHardware();
    fetchAlerts();
    fetchSummary();
    setInterval(refreshCameras, 5000);
    setInterval(fetchAlerts, 2500);
    setInterval(fetchSummary, 3000);
    setInterval(fetchAvailableSources, 15000);
    setInterval(checkSystemHardware, 30000);
});
