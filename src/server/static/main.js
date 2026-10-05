document.addEventListener("DOMContentLoaded", () => {
    const addCameraBtn = document.getElementById("add-camera-btn");
    const modal = document.getElementById("camera-modal");
    const closeBtn = document.querySelector(".close-btn");
    const form = document.getElementById("add-camera-form");
    const grid = document.getElementById("camera-grid");

    // Modal logic
    addCameraBtn.onclick = () => modal.style.display = "flex";
    closeBtn.onclick = () => modal.style.display = "none";
    window.onclick = (e) => {
        if (e.target == modal) modal.style.display = "none";
    }

    // Add camera form submit
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            name: document.getElementById("cam-name").value,
            type: document.getElementById("cam-type").value,
            url: document.getElementById("cam-url").value,
            username: document.getElementById("cam-user").value,
            password: document.getElementById("cam-pass").value,
            verify_tls: document.getElementById("cam-tls").checked
        };

        try {
            const res = await fetch("/api/cameras", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if(data.status === "success") {
                modal.style.display = "none";
                form.reset();
                refreshCameras();
            } else {
                alert("Failed to add camera");
            }
        } catch (err) {
            console.error(err);
            alert("Error adding camera");
        }
    });

    async function refreshCameras() {
        try {
            const res = await fetch("/api/cameras");
            const data = await res.json();
            renderGrid(data.cameras);
        } catch (err) {
            console.error("Failed to fetch cameras", err);
        }
    }

    function renderGrid(cameras) {
        if (!cameras || cameras.length === 0) {
            grid.innerHTML = '<div style="color:var(--text-secondary); width: 100%;">No cameras active. Click "Add Camera" to start.</div>';
            return;
        }

        grid.innerHTML = "";
        cameras.forEach(cam => {
            const statusClass = cam.is_alive ? "ok" : "offline";
            const statusText = cam.is_alive ? "LIVE" : "OFFLINE";
            
            // Only add the image tag if it's alive, else placeholder
            const streamContent = cam.is_alive 
                ? `<img src="/stream/${cam.name}" class="mjpeg-stream" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"/>
                   <div class="placeholder-text" style="display:none;">Stream Error</div>`
                : `<div class="placeholder-text">Camera Offline</div>`;

            const card = document.createElement("div");
            card.className = "camera-card glass-panel";
            card.innerHTML = `
                <div class="camera-header">
                    <h3>${cam.name}</h3>
                    <span class="badge ${statusClass}">${statusText}</span>
                </div>
                <div class="video-container">
                    ${streamContent}
                </div>
            `;
            grid.appendChild(card);
        });
    }

    // Initial load and periodic refresh
    refreshCameras();
    setInterval(refreshCameras, 5000);
});
