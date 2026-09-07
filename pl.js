(async()=>{
  const el=document.getElementById("proposal-data");
  if(el && !el.textContent.trim() && el.dataset.src){
    const r=await fetch(el.dataset.src,{cache:"no-store"});
    if(!r.ok) throw new Error("No se pudo cargar la propuesta");
    el.textContent=await r.text();
  }

  const proposal = JSON.parse(document.getElementById("proposal-data").textContent);
  const days = Object.fromEntries(proposal.days.map((day) => [day.id, day]));
  const statusMeta = { pending: "Pendiente", approved: "Aprobado", changes: "Pedir cambios" };
  const storageKey = "partners-weekly-review-2026-09-07";
  const defaultState = { statuses: { monday: "pending", wednesday: "pending", friday: "pending" }, notes: "" };
  let state = defaultState;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (saved) state = { statuses: { ...defaultState.statuses, ...(saved.statuses || {}) }, notes: typeof saved.notes === "string" ? saved.notes : "" };
  } catch {}

  const toast = document.querySelector(".toast");
  let toastTimer;
  const notify = (message = "Copiado ✓") => {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 1500);
  };
  const copy = async (value) => {
    try { await navigator.clipboard.writeText(value); }
    catch {
      const area = document.createElement("textarea");
      area.value = value; area.style.position = "fixed"; area.style.opacity = "0";
      document.body.append(area); area.select(); document.execCommand("copy"); area.remove();
    }
    notify();
  };
  const persist = () => { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch {} };
  const escapeMarkup = (value) => String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));

  const updatePlatform = (article, platform) => {
    const day = days[article.dataset.day];
    const item = day.platforms[platform];
    article.dataset.platform = platform;
    article.querySelectorAll("[data-platform]").forEach((button) => {
      const active = button.dataset.platform === platform;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    });
    article.querySelector("[data-caption-label]").textContent = "CAPTION · " + item.label.toUpperCase();
    article.querySelector("[data-caption-note]").textContent = item.note;
    article.querySelector("[data-caption-body]").textContent = item.caption;
    const tags = article.querySelector("[data-tags]");
    tags.innerHTML = item.hashtags.length ? '<div class="tag-list">' + item.hashtags.map((tag) => '<span>' + escapeMarkup(tag) + '</span>').join("") + '</div>' : '<p class="empty-note">Sin hashtags — recomendado para Google Business Profile.</p>';
    article.querySelector("[data-copy-tags]").style.display = item.hashtags.length ? "block" : "none";
    article.querySelector("[data-link-anchor]").href = item.url;
    article.querySelector("[data-link-text]").textContent = item.url;
  };

  const updateReview = () => {
    const approved = Object.values(state.statuses).filter((status) => status === "approved").length;
    document.querySelector("[data-approved-count]").textContent = approved + "/3";
    document.querySelector("[data-approval-heading]").textContent = approved === 3 ? "Semana aprobada." : approved + " de 3 piezas aprobadas.";
    proposal.days.forEach((day) => {
      const status = state.statuses[day.id];
      const article = document.querySelector('[data-day="' + day.id + '"]');
      const pill = article.querySelector("[data-status-pill]");
      pill.className = "status-pill " + status;
      pill.textContent = statusMeta[status];
      article.querySelectorAll("[data-set-status]").forEach((button) => button.className = button.dataset.setStatus === status ? "selected " + status : "");
      const summary = document.querySelector('[data-summary-status="' + day.id + '"]');
      summary.className = status;
      summary.textContent = statusMeta[status];
    });
  };

  const downloadCreative = async (dayId) => {
    const day = days[dayId];
    const image = document.getElementById("creative-img-" + dayId);
    if (!image.complete) await image.decode();
    const canvas = document.createElement("canvas");
    canvas.width = 1200; canvas.height = 1200;
    const ctx = canvas.getContext("2d");
    const scale = Math.max(1200 / image.naturalWidth, 1200 / image.naturalHeight);
    const sw = 1200 / scale; const sh = 1200 / scale;
    ctx.drawImage(image, (image.naturalWidth - sw) / 2, (image.naturalHeight - sh) / 2, sw, sh, 0, 0, 1200, 1200);
    const gradient = ctx.createLinearGradient(day.overlay === "right" ? 1200 : 0, 0, day.overlay === "right" ? 500 : 700, 0);
    gradient.addColorStop(0, "rgba(8,10,21,.92)"); gradient.addColorStop(.55, "rgba(8,10,21,.56)"); gradient.addColorStop(1, "rgba(8,10,21,0)");
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, 1200, 1200);
    const footerGradient = ctx.createLinearGradient(0, 830, 0, 1200);
    footerGradient.addColorStop(0, "rgba(8,10,21,0)"); footerGradient.addColorStop(1, "rgba(8,10,21,.8)");
    ctx.fillStyle = footerGradient; ctx.fillRect(0, 760, 1200, 440);
    const x = day.overlay === "right" ? 1128 : 72;
    ctx.textAlign = day.overlay === "right" ? "right" : "left";
    ctx.fillStyle = "#fff"; ctx.font = "600 26px Arial"; ctx.fillText("PARTNERS LIMOS", x, 88);
    ctx.fillStyle = "#d2ad4f"; ctx.fillRect(day.overlay === "right" ? 1128 : 72, 112, day.overlay === "right" ? -72 : 72, 3);
    const textY = day.id === "friday" ? 285 : 310;
    ctx.fillStyle = "#d2ad4f"; ctx.font = "700 23px Arial"; ctx.fillText(day.eyebrow, x, textY);
    ctx.fillStyle = "#fff"; ctx.font = "600 76px Georgia";
    day.headlineLines.forEach((line, index) => ctx.fillText(line, x, textY + 92 + index * 86));
    ctx.font = "400 27px Arial"; ctx.fillStyle = "rgba(255,255,255,.9)"; ctx.fillText(day.subline, x, textY + 92 + day.headlineLines.length * 86 + 28);
    ctx.textAlign = "left"; ctx.font = "600 22px Arial"; ctx.fillStyle = "rgba(255,255,255,.88)"; ctx.fillText("NEW JERSEY · NYC · 24/7", 72, 1128);
    ctx.textAlign = "right"; ctx.fillStyle = "#d2ad4f"; ctx.fillText("GET AN INSTANT QUOTE  →", 1128, 1128);
    const anchor = document.createElement("a");
    anchor.href = canvas.toDataURL("image/png");
    anchor.download = "partners-limos-" + day.id + "-07-11-september-2026-1200x1200.png";
    anchor.click();
  };

  document.querySelectorAll("[data-day]").forEach((article) => {
    article.dataset.platform = "instagram";
    article.querySelectorAll("[data-platform]").forEach((button) => button.addEventListener("click", () => updatePlatform(article, button.dataset.platform)));
    article.querySelector("[data-copy-caption]").addEventListener("click", () => {
      const item = days[article.dataset.day].platforms[article.dataset.platform];
      copy((item.caption + "\n\n" + item.hashtags.join(" ")).trim());
    });
    article.querySelector("[data-copy-tags]").addEventListener("click", () => copy(days[article.dataset.day].platforms[article.dataset.platform].hashtags.join(" ")));
    article.querySelector("[data-copy-link]").addEventListener("click", () => copy(days[article.dataset.day].platforms[article.dataset.platform].url));
    article.querySelectorAll("[data-copy-value]").forEach((button) => button.addEventListener("click", () => copy(button.dataset.copyValue)));
    article.querySelector("[data-download-creative]").addEventListener("click", (event) => downloadCreative(event.currentTarget.dataset.downloadCreative));
    article.querySelectorAll("[data-set-status]").forEach((button) => button.addEventListener("click", () => {
      state.statuses[article.dataset.day] = button.dataset.setStatus;
      persist(); updateReview();
    }));
  });

  const notes = document.getElementById("review-notes");
  notes.value = state.notes;
  notes.addEventListener("input", () => { state.notes = notes.value; persist(); });
  document.getElementById("print-page").addEventListener("click", () => window.print());
  document.getElementById("download-summary").addEventListener("click", () => {
    const lines = ["PARTNERS LIMOS — APROBACIÓN DE CONTENIDO", "Semana: " + proposal.week, "", ...proposal.days.flatMap((day) => [day.day.toUpperCase() + " " + day.date + ": " + statusMeta[state.statuses[day.id]], "Concepto: " + day.title, ""]), "NOTAS DE REVISIÓN", state.notes || "Sin notas."];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "partners-limos-aprobacion-07-11-septiembre-2026.txt"; anchor.click(); URL.revokeObjectURL(url);
  });

  const menu = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".week-nav");
  menu.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    menu.setAttribute("aria-expanded", String(open));
    menu.textContent = open ? "Cerrar" : "Semana";
  });
  nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => { nav.classList.remove("is-open"); menu.setAttribute("aria-expanded", "false"); menu.textContent = "Semana"; }));
  updateReview();

})();
