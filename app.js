(function () {
  let selectedCategory = document.querySelector("#category-group .chip")?.dataset.category || "quotes";
  const selectedAspects = new Set(
    [...document.querySelectorAll("#aspect-group .chip.chip-active")].map(c => c.dataset.aspect)
  );

  // --- Category chips ---
  document.querySelectorAll("#category-group .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#category-group .chip").forEach(c => c.classList.remove("chip-active"));
      chip.classList.add("chip-active");
      selectedCategory = chip.dataset.category;
    });
  });

  // --- Aspect chips (multi-select) ---
  document.querySelectorAll("#aspect-group .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const aspect = chip.dataset.aspect;
      if (selectedAspects.has(aspect)) {
        if (selectedAspects.size > 1) { // keep at least one selected
          selectedAspects.delete(aspect);
          chip.classList.remove("chip-active");
        }
      } else {
        selectedAspects.add(aspect);
        chip.classList.add("chip-active");
      }
    });
  });

  // --- Random button clears topic ---
  document.getElementById("random-btn").addEventListener("click", () => {
    document.getElementById("topic-input").value = "";
  });

  // --- Queue submission ---
  const queueBtn = document.getElementById("queue-btn");
  const feedback = document.getElementById("queue-feedback");

  queueBtn.addEventListener("click", async () => {
    const topic = document.getElementById("topic-input").value.trim();
    const quantity = parseInt(document.getElementById("quantity-input").value, 10) || 1;
    const duration = parseFloat(document.getElementById("duration-input").value) || 8;

    queueBtn.disabled = true;
    feedback.textContent = "Queuing...";
    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: selectedCategory,
          topic: topic,
          is_random: topic.length === 0,
          aspects: [...selectedAspects],
          quantity: quantity,
          duration: duration,
        }),
      });
      const data = await res.json();
      if (data.ok) {
        feedback.textContent = `Queued ${data.queued} video(s). Watch progress below.`;
        refreshQueue();
      } else {
        feedback.textContent = data.error || "Something went wrong.";
      }
    } catch (e) {
      feedback.textContent = "Network error while queuing.";
    } finally {
      queueBtn.disabled = false;
    }
  });

  // --- Queue polling ---
  const queueList = document.getElementById("queue-list");
  const queueCounts = document.getElementById("queue-counts");

  function statusClass(status) {
    return { pending: "status-pending", processing: "status-processing", done: "status-done", error: "status-error" }[status] || "status-pending";
  }

  async function refreshQueue() {
    try {
      const res = await fetch("/api/queue");
      const data = await res.json();
      const counts = data.counts || {};
      queueCounts.innerHTML = ["pending", "processing", "done", "error"]
        .filter(k => counts[k])
        .map(k => `<span class="count-badge">${k}: ${counts[k]}</span>`)
        .join("");

      if (!data.jobs.length) {
        queueList.innerHTML = '<p class="empty-state">No jobs yet.</p>';
      } else {
        queueList.innerHTML = data.jobs.slice(0, 30).map(job => `
          <div class="queue-item">
            <div class="queue-item-left">
              <span>${job.category} · ${job.aspect}</span>
              <span class="queue-item-topic">${job.is_random ? "random topic" : (job.topic || "")}</span>
            </div>
            <span class="status-badge ${statusClass(job.status)}">${job.status}</span>
          </div>
        `).join("");
      }

      // If anything is pending/processing, keep polling gallery too (new videos appear)
      if ((counts.pending || counts.processing)) {
        refreshGallery();
      }
    } catch (e) { /* ignore transient errors */ }
  }

  // --- Gallery ---
  const galleryGrid = document.getElementById("gallery-grid");
  const galleryFilter = document.getElementById("gallery-filter");
  let videosCache = [];

  function truncate(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

  async function refreshGallery() {
    const category = galleryFilter.value;
    try {
      const res = await fetch(`/api/videos?category=${encodeURIComponent(category)}`);
      const data = await res.json();
      videosCache = data.videos;
      if (!videosCache.length) {
        galleryGrid.innerHTML = '<p class="empty-state">No videos generated yet.</p>';
        return;
      }
      galleryGrid.innerHTML = videosCache.map(v => `
        <div class="gallery-item" data-aspect="${v.aspect}" data-id="${v.id}">
          <img class="gallery-thumb" loading="lazy" src="/media/thumb/${v.id}" alt="">
          <div class="gallery-meta">
            <div class="gallery-cat">${v.category}</div>
            <div class="gallery-text">${truncate(v.text_content, 70)}</div>
          </div>
        </div>
      `).join("");
      galleryGrid.querySelectorAll(".gallery-item").forEach(el => {
        el.addEventListener("click", () => openPreview(parseInt(el.dataset.id, 10)));
      });
    } catch (e) { /* ignore */ }
  }

  galleryFilter.addEventListener("change", refreshGallery);

  // --- Preview modal ---
  const modal = document.getElementById("preview-modal");
  const modalVideo = document.getElementById("modal-video");
  const modalInfo = document.getElementById("modal-info");
  const modalDownload = document.getElementById("modal-download");
  const modalDelete = document.getElementById("modal-delete");
  let currentVideoId = null;

  function openPreview(id) {
    const v = videosCache.find(x => x.id === id);
    if (!v) return;
    currentVideoId = id;
    modalVideo.src = `/media/video/${id}`;
    modalInfo.innerHTML = `
      <strong>${v.category}</strong> · ${v.aspect} · ${v.duration}s<br>
      "${v.text_content}"<br>
      Style: ${v.palette} · ${v.font} · ${v.animation} · music: ${v.music_mood}
    `;
    modalDownload.href = `/download/${id}`;
    modal.classList.add("open");
  }

  document.getElementById("modal-close").addEventListener("click", closePreview);
  modal.addEventListener("click", (e) => { if (e.target === modal) closePreview(); });

  function closePreview() {
    modal.classList.remove("open");
    modalVideo.pause();
    modalVideo.src = "";
    currentVideoId = null;
  }

  modalDelete.addEventListener("click", async () => {
    if (currentVideoId == null) return;
    if (!confirm("Delete this video permanently?")) return;
    await fetch(`/delete/${currentVideoId}`, { method: "POST" });
    closePreview();
    refreshGallery();
  });

  // --- Init ---
  refreshQueue();
  refreshGallery();
  setInterval(refreshQueue, 2500);
})();
