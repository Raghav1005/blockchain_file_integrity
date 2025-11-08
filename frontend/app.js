// ===========================
// Sequential Background Videos (guarded if #bg-video missing)
// ===========================
const bgVideo = document.getElementById("bg-video");
if (bgVideo) {
  const videoList = ["background.mp4", "background2.mp4", "background3.mp4"];
  let currentVideo = 0;
  function playNextVideo() {
    bgVideo.src = videoList[currentVideo];
    bgVideo.load();
    bgVideo.play().catch(err => console.error("Video playback error:", err));
    bgVideo.onended = () => {
      currentVideo = (currentVideo + 1) % videoList.length;
      playNextVideo();
    };
  }
  window.addEventListener("DOMContentLoaded", playNextVideo);
}

// ===========================
// Log Helper
// ===========================
const log = (msg, type = "") => {
  const systemLog = document.getElementById("systemLog");
  if (!systemLog) return;
  const icon =
    type === "success" ? "✅" :
    type === "error" ? "❌" :
    type === "info" ? "ℹ️" :
    type === "warn" ? "⚠️" : "";
  systemLog.textContent += `\n${icon} ${msg}`;
  systemLog.scrollTop = systemLog.scrollHeight;
};

// ===========================
// FRONTEND INTERACTIONS (IDs match your HTML)
// ===========================
const registerBtn = document.getElementById("btnRegister");
const verifyBtn   = document.getElementById("btnVerify");
const validateBtn = document.getElementById("btnValidate");
const historyBtn  = document.getElementById("btnHistory");
const myHistoryBtn= document.getElementById("btnMyHistory");
const demoBtn     = document.getElementById("btnDemo"); // may be null (no demo button)

const API_BASE = "http://127.0.0.1:5000";

// Auto-fill uploader with logged-in username
window.addEventListener("DOMContentLoaded", () => {
  const user = localStorage.getItem("username");
  const uploaderField = document.getElementById("uploaderId");
  if (user && uploaderField) uploaderField.value = user;
});

// ===========================
// Register File
// ===========================
if (registerBtn) registerBtn.addEventListener("click", async () => {
  const fileInput = document.getElementById("registerFile");
  const uploaderId = (document.getElementById("uploaderId")?.value || "").trim();

  if (!fileInput?.files?.[0]) return log("No file selected for registration.", "warn");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (uploaderId) formData.append("uploader_id", uploaderId);

  log(`Registering ${fileInput.files[0].name}...`, "info");

  try {
    const res = await fetch(`${API_BASE}/register`, { method: "POST", body: formData });
    const data = await res.json();
    log(data.message || "Registration complete", data.success ? "success" : "error");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});

// ===========================
// Verify File
// ===========================
if (verifyBtn) verifyBtn.addEventListener("click", async () => {
  const fileInput = document.getElementById("verifyFile");
  if (!fileInput?.files?.[0]) return log("No file selected for verification.", "warn");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  log(`Verifying ${fileInput.files[0].name}...`, "info");

  try {
    const res = await fetch(`${API_BASE}/verify`, { method: "POST", body: formData });
    const data = await res.json();
    log(data.message || "Verification complete", data.success ? "success" : "error");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});

// ===========================
// View Full Blockchain History
// ===========================
if (historyBtn) historyBtn.addEventListener("click", async () => {
  log("Fetching file history...", "info");
  try {
    const res = await fetch(`${API_BASE}/history`);
    const data = await res.json();
    log(`File History:\n${JSON.stringify(data, null, 2)}`, "success");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});

// ===========================
// Validate Blockchain
// ===========================
if (validateBtn) validateBtn.addEventListener("click", async () => {
  log("Validating blockchain integrity...", "info");
  try {
    const res = await fetch(`${API_BASE}/validate`);
    const data = await res.json();
    log(data.message || "Validation complete", data.success ? "success" : "error");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});

// ===========================
// Demo Simulation (only if button exists)
// ===========================
if (demoBtn) demoBtn.addEventListener("click", async () => {
  log("Running demo simulation...", "info");
  try {
    const res = await fetch(`${API_BASE}/demo`);
    const data = await res.json();
    log(data.message || "Demo finished", "success");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});

// ===========================
// My Upload History (User-Specific) — Pretty Log Output
// ===========================
myHistoryBtn.addEventListener("click", async () => {
  const username = localStorage.getItem("username");
  if (!username) return log("⚠️ Login required to view your history.", "warn");

  log(`fetching upload history for ${username}...`, "info");

  try {
    const res = await fetch(`${API_BASE}/api/history_user?username=${encodeURIComponent(username)}`);
    const data = await res.json();

    if (!res.ok || !data.success) {
      return log(`Error: ${data.message || data.error || "Failed to load history"}`, "error");
    }
    if (!data.blocks || data.blocks.length === 0) {
      return log(`📂 Upload History for ${username} (0 files)`, "warn");
    }

    // helpers
    const humanSize = bytes =>
      typeof bytes === "number" && bytes >= 0
        ? (bytes >= 1024 * 1024
            ? `${(bytes / (1024 * 1024)).toFixed(2)} MB`
            : bytes >= 1024
              ? `${(bytes / 1024).toFixed(2)} KB`
              : `${bytes} B`)
        : "N/A";

    const shortHash = h => (h ? `${h.slice(0, 7)}...${h.slice(-4)}` : "N/A");
    const niceTime = ts =>
      ts ? new Date(ts * 1000).toLocaleString(undefined, { month: "2-digit", day: "2-digit", year: "numeric", hour: "numeric", minute: "2-digit" }) : "N/A";
    const baseName = p => (p ? p.split(/[\\/]/).pop() : "N/A");

    const lines = [];
    lines.push(`📂 Upload History for ${username} (${data.blocks.length} ${data.blocks.length === 1 ? "file" : "files"}):\n`);

    data.blocks.forEach((b, i) => {
      lines.push(
        `${i + 1}) ${baseName(b.filename)}\n` +
        `   • Action: ${b.action || "N/A"}\n` +
        `   • File Hash: ${shortHash(b.file_hash)}\n` +
        `   • File Size: ${humanSize(b.file_size)}\n` +
        `   • Block Index: ${b.index}\n` +
        `   • Time: ${niceTime(b.timestamp)}`
      );
    });

    log(lines.join("\n"), "success");
  } catch (err) {
    log(`Server error: ${err.message}`, "error");
  }
});
