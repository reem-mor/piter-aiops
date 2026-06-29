(() => {
  const MIN_LEN = 3;
  const MAX_LEN = 500;
  const RESOLVED_KEY = "piter_resolved_alerts";
  const SAVED_MIN_KEY = "piter_saved_min";
  const SAVED_IMPACT_KEY = "piter_saved_impact";

  const STOP = new Set([
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "it", "this", "that",
    "what", "who", "when", "where", "why", "how", "which", "about",
  ]);

  function tokenize(text) {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((t) => t.length > 1 && !STOP.has(t));
  }

  function validateQuestion(text) {
    const trimmed = (text || "").trim();
    if (!trimmed) return "Please enter a question.";
    if (trimmed.length < MIN_LEN) return "Type a question with at least 3 characters.";
    if (trimmed.length > MAX_LEN) return `Question too long (${trimmed.length}/${MAX_LEN}).`;
    if (tokenize(trimmed).length === 0) return "Your question has no searchable keywords. Try rephrasing.";
    return null;
  }

  function readResolvedSet() {
    try {
      const raw = localStorage.getItem(RESOLVED_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch {
      return new Set();
    }
  }

  function writeResolvedSet(set) {
    localStorage.setItem(RESOLVED_KEY, JSON.stringify([...set]));
  }

  function bindCharCounter(inputId, counterId) {
    const input = document.getElementById(inputId);
    const counter = document.getElementById(counterId);
    if (!input || !counter) return;
    const update = () => {
      counter.textContent = `${input.value.length}/${MAX_LEN}`;
    };
    input.addEventListener("input", update);
    update();
  }

  function bindClientValidation(formId, inputId) {
    const form = document.getElementById(formId);
    const input = document.getElementById(inputId);
    if (!form || !input) return;
    form.addEventListener("submit", (event) => {
      const err = validateQuestion(input.value);
      if (err) {
        event.preventDefault();
        alert(err);
      }
    });
  }

  function updateAlertHeader(btn) {
    const meta = document.getElementById("workflow-alert-meta");
    const title = document.getElementById("workflow-alert-title");
    const service = document.getElementById("workflow-alert-service");
    if (!btn) return;
    if (meta) meta.textContent = `Alert ${btn.dataset.alertId || ""} · ${btn.dataset.source || ""}`;
    if (title) title.textContent = btn.dataset.title || "";
    if (service) service.textContent = btn.dataset.service || "";
  }

  function resetWorkflowStages() {
    document.querySelectorAll(".stage-pill").forEach((pill) => {
      pill.classList.remove("is-active", "is-done");
    });
  }

  function setWorkflowStagesDone() {
    document.querySelectorAll(".stage-pill").forEach((pill) => {
      pill.classList.add("is-done");
      pill.classList.remove("is-active");
    });
  }

  function animateWorkflowStages() {
    resetWorkflowStages();
    const pills = [...document.querySelectorAll(".stage-pill")];
    const delays = [0, 450, 950, 1450];
    pills.forEach((pill, index) => {
      window.setTimeout(() => {
        pills.forEach((p, j) => {
          p.classList.toggle("is-done", j < index);
          p.classList.toggle("is-active", j === index);
        });
      }, delays[index] || 0);
    });
  }

  function setSubmitLabel(triaging) {
    const btn = document.getElementById("workflow-submit");
    if (!btn) return;
    const label = btn.querySelector(".btn-label");
    if (label) {
      label.textContent = triaging ? "Triaging…" : "Run triage";
    }
    btn.disabled = Boolean(triaging);
    btn.setAttribute("aria-busy", triaging ? "true" : "false");
  }

  function refreshResolvedUi() {
    const resolved = readResolvedSet();
    document.querySelectorAll(".alert-item").forEach((btn) => {
      const id = btn.dataset.alertId;
      const isResolved = Boolean(id && resolved.has(id));
      btn.classList.toggle("is-resolved", isResolved);
      const badge = btn.querySelector(".alert-resolved-badge");
      if (badge) badge.hidden = !isResolved;
    });

    const host = document.querySelector(".workflow-resolve-host");
    if (host) {
      const alertId = host.dataset.alertId;
      const already = alertId && resolved.has(alertId);
      const btn = host.querySelector("#mark-resolved-btn");
      const note = host.querySelector("#workflow-resolved-note");
      if (btn) btn.hidden = already;
      if (note) note.hidden = !already;
    }
  }

  function restoreSessionMetrics() {
    const savedEl = document.getElementById("total-saved-min");
    const impactEl = document.getElementById("total-saved-impact");
    if (savedEl) savedEl.textContent = localStorage.getItem(SAVED_MIN_KEY) || "0";
    if (impactEl) {
      const val = Number(localStorage.getItem(SAVED_IMPACT_KEY) || 0);
      impactEl.textContent = `$${val.toLocaleString()}`;
    }
  }

  function bindAlertPicker() {
    const list = document.getElementById("alert-list");
    if (!list) return;
    const alertIdInput = document.getElementById("workflow-alert-id");
    const questionInput = document.getElementById("workflow-question");
    const result = document.getElementById("workflow-result");

    list.addEventListener("click", (event) => {
      const btn = event.target.closest(".alert-item");
      if (!btn) return;
      list.querySelectorAll(".alert-item").forEach((el) => el.classList.remove("is-active"));
      btn.classList.add("is-active");
      if (alertIdInput) alertIdInput.value = btn.dataset.alertId || "";
      if (questionInput) questionInput.value = btn.dataset.question || "";
      updateAlertHeader(btn);
      resetWorkflowStages();
      setSubmitLabel(false);
      if (result) result.innerHTML = "";
    });

    const active = list.querySelector(".alert-item.is-active");
    if (active) updateAlertHeader(active);
    refreshResolvedUi();
  }

  function bindMarkResolved() {
    document.body.addEventListener("click", (event) => {
      const btn = event.target.closest("#mark-resolved-btn");
      if (!btn) return;
      const host = btn.closest(".workflow-resolve-host");
      if (!host) return;

      const alertId = host.dataset.alertId;
      const savedMin = Number(host.dataset.savedMin || 0);
      const savedImpact = Number(host.dataset.savedImpact || 0);
      if (!alertId || savedMin <= 0) return;

      const resolved = readResolvedSet();
      if (resolved.has(alertId)) {
        refreshResolvedUi();
        return;
      }
      resolved.add(alertId);
      writeResolvedSet(resolved);

      const nextMin = Number(localStorage.getItem(SAVED_MIN_KEY) || 0) + savedMin;
      const nextImpact = Number(localStorage.getItem(SAVED_IMPACT_KEY) || 0) + savedImpact;
      localStorage.setItem(SAVED_MIN_KEY, String(nextMin));
      localStorage.setItem(SAVED_IMPACT_KEY, String(nextImpact));
      restoreSessionMetrics();
      refreshResolvedUi();
    });
  }

  function bindArchitecture() {
    const blocks = document.querySelectorAll("[data-arch-block]");
    const detail = document.getElementById("arch-detail");
    if (!blocks.length || !detail) return;
    blocks.forEach((block) => {
      block.addEventListener("click", () => {
        blocks.forEach((b) => b.classList.remove("is-active"));
        block.classList.add("is-active");
        const key = block.dataset.archBlock;
        detail.querySelectorAll("[data-arch-panel]").forEach((panel) => {
          panel.hidden = panel.dataset.archPanel !== key;
        });
      });
    });
  }

  function bindWorkflowStages() {
    document.body.addEventListener("htmx:beforeRequest", (event) => {
      const elt = event.detail.elt;
      if (!elt || elt.id !== "workflow-form") return;
      animateWorkflowStages();
      setSubmitLabel(true);
    });

    document.body.addEventListener("htmx:afterSwap", (event) => {
      if (event.detail.target?.id !== "workflow-result") return;
      setWorkflowStagesDone();
      setSubmitLabel(false);
      refreshResolvedUi();
    });

    document.body.addEventListener("htmx:responseError", (event) => {
      if (event.detail.elt?.id !== "workflow-form") return;
      resetWorkflowStages();
      setSubmitLabel(false);
    });
  }

  function bindUploadValidation() {
    const form = document.getElementById("upload-form");
    const input = document.getElementById("document");
    if (!form || !input) return;
    const maxMb = 5;
    const maxBytes = maxMb * 1024 * 1024;
    const allowed = [".md", ".txt", ".csv", ".docx", ".pdf"];
    form.addEventListener("submit", (event) => {
      const file = input.files?.[0];
      if (!file) {
        event.preventDefault();
        alert("Choose a file to upload.");
        return;
      }
      if (file.size === 0) {
        event.preventDefault();
        alert("File is empty.");
        return;
      }
      if (file.size > maxBytes) {
        event.preventDefault();
        alert(`File is too large. Maximum size is ${maxMb} MB.`);
        return;
      }
      const name = file.name.toLowerCase();
      if (!allowed.some((ext) => name.endsWith(ext))) {
        event.preventDefault();
        alert(`Unsupported file type. Allowed: ${allowed.join(", ")}`);
      }
    });
  }

  function bindSystemGuide() {
    const dialog = document.getElementById("system-guide");
    if (!dialog || typeof dialog.showModal !== "function") return;

    const open = () => {
      if (!dialog.open) dialog.showModal();
    };
    const close = () => {
      if (dialog.open) dialog.close();
    };

    document.querySelectorAll("[data-open-guide]").forEach((el) => {
      el.addEventListener("click", open);
    });
    document.querySelectorAll("[data-close-guide]").forEach((el) => {
      el.addEventListener("click", close);
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close();
    });
  }

  function bindHtmxErrors() {
    document.body.addEventListener("htmx:responseError", () => {
      const targets = ["answer", "workflow-result", "upload-result"];
      targets.forEach((id) => {
        const el = document.getElementById(id);
        if (!el || el.innerHTML.trim()) return;
        el.innerHTML =
          '<article class="workflow-panel workflow-panel-error"><header class="workflow-panel-head"><span class="badge badge-error">⚠ Error</span></header><p class="workflow-panel-body">Service unavailable. Check that the app is running and try again.</p></article>';
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindCharCounter("question", "char-count");
    bindClientValidation("ask-form", "question");
    bindClientValidation("workflow-form", "workflow-question");
    bindAlertPicker();
    bindArchitecture();
    bindWorkflowStages();
    bindMarkResolved();
    bindUploadValidation();
    bindSystemGuide();
    restoreSessionMetrics();
    bindHtmxErrors();
  });
})();
