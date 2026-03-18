const state = {
  skills: [],
  certifications: [],
  languages: [],
  experience: [],
  education: [],
  currentId: null,
  whatsappSent: false,
  flags: {},
};


const $ = id => document.getElementById(id);
const val = id => $(id)?.value.trim() || "";

function show(id) { $(id)?.classList.remove("hidden"); }
function hide(id) { $(id)?.classList.add("hidden"); }

function autoCap(text) {
  const stop = new Set(["a","an","the","and","or","but","in","on","at","to","for","of","with","by","from","as","is","was","are"]);
  return text.trim().split(" ").map((w, i) =>
    i === 0 || !stop.has(w.toLowerCase()) ? w.charAt(0).toUpperCase() + w.slice(1) : w.toLowerCase()
  ).join(" ");
}

function setLastEdited() {
  const now = new Date();
  const d = now.toLocaleDateString("en-IN", {day:"numeric",month:"long",year:"numeric"});
  const t = now.toLocaleTimeString("en-IN", {hour:"2-digit",minute:"2-digit",hour12:true}).toUpperCase();
  $("lastEdited").textContent = `Last Edited: ${d} – ${t}`;
}

function validateEmail(e) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e); }
function validatePhone(p) {
  if (!p) return true;
  const c = p.replace(/[\s\-\(\)\+]/g, "");
  return /^\d{7,15}$/.test(c);
}


function addSkill() {
  const input = $("skillInput");
  const raw = input.value.trim();
  if (!raw) return;
  const capped = autoCap(raw);
  if (state.skills.includes(capped)) {
    const w = $("dupWarn");
    w.textContent = `Duplicate skill detected: ${capped}`;
    w.classList.remove("hidden");
    setTimeout(() => w.classList.add("hidden"), 3000);
    return;
  }
  hide("dupWarn");
  state.skills.push(capped);
  input.value = "";
  renderTags("skillTags", state.skills, "skills");
  liveUpdate();
}

function addSimple(listKey, inputId) {
  const input = $(inputId);
  const raw = input.value.trim();
  if (!raw) return;
  const capped = autoCap(raw);
  state[listKey].push(capped);
  input.value = "";
  const containerId = listKey === "certifications" ? "certTags" : "langTags";
  renderTags(containerId, state[listKey], listKey);
  liveUpdate();
}

function removeFromList(listKey, idx) {
  state[listKey].splice(idx, 1);
  if (listKey === "skills") renderTags("skillTags", state.skills, "skills");
  else if (listKey === "certifications") renderTags("certTags", state.certifications, "certifications");
  else if (listKey === "languages") renderTags("langTags", state.languages, "languages");
  liveUpdate();
}

function renderTags(containerId, arr, listKey) {
  $(containerId).innerHTML = arr.map((s, i) =>
    `<div class="tag">${s}<button class="tag-remove" onclick="removeFromList('${listKey}',${i})">×</button></div>`
  ).join("");
}


function addEntry(type) {
  const id = Date.now();
  if (type === "experience") {
    state.experience.push({ _id: id, role: "", company: "", duration: "", description: "" });
    renderExpList();
  } else {
    state.education.push({ _id: id, degree: "", institution: "", year: "" });
    renderEduList();
  }
}

function removeEntry(type, id) {
  if (type === "experience") {
    state.experience = state.experience.filter(e => e._id !== id);
    renderExpList();
  } else {
    state.education = state.education.filter(e => e._id !== id);
    renderEduList();
  }
  liveUpdate();
}

function updateEntry(type, id, field, value) {
  const list = type === "experience" ? state.experience : state.education;
  const item = list.find(e => e._id === id);
  if (item) { item[field] = value; liveUpdate(); }
}

function renderExpList() {
  $("expList").innerHTML = state.experience.map(e => `
    <div class="entry-item">
      <button class="entry-remove" onclick="removeEntry('experience',${e._id})">×</button>
      <div class="entry-grid">
        <div class="field">
          <label>Job Title</label>
          <input type="text" value="${e.role}" placeholder="python developer"
            oninput="updateEntry('experience',${e._id},'role',this.value)"/>
        </div>
        <div class="field">
          <label>Company</label>
          <input type="text" value="${e.company}" placeholder="CRCCF"
            oninput="updateEntry('experience',${e._id},'company',this.value)"/>
        </div>
      </div>
      <div class="field">
        <label>Duration</label>
        <input type="text" value="${e.duration}" placeholder="Jan 2022 – Present"
          oninput="updateEntry('experience',${e._id},'duration',this.value)"/>
      </div>
      <div class="field">
        <label>Description</label>
        <textarea rows="2" placeholder="Key responsibilities and achievements..."
          oninput="updateEntry('experience',${e._id},'description',this.value)">${e.description}</textarea>
      </div>
    </div>
  `).join("");
}

function renderEduList() {
  $("eduList").innerHTML = state.education.map(e => `
    <div class="entry-item">
      <button class="entry-remove" onclick="removeEntry('education',${e._id})">×</button>
      <div class="entry-grid">
        <div class="field">
          <label>Degree / Course</label>
          <input type="text" value="${e.degree}" placeholder="B.Tech Computer Science"
            oninput="updateEntry('education',${e._id},'degree',this.value)"/>
        </div>
        <div class="field">
          <label>Institution</label>
          <input type="text" value="${e.institution}" placeholder="NIT Bbsr"
            oninput="updateEntry('education',${e._id},'institution',this.value)"/>
        </div>
      </div>
      <div class="field">
        <label>Year</label>
        <input type="text" value="${e.year}" placeholder="2022 – 2026"
          oninput="updateEntry('education',${e._id},'year',this.value)"/>
      </div>
    </div>
  `).join("");
}


$("name").addEventListener("blur", () => {
  const raw = val("name");
  if (!raw) return;
  const capped = autoCap(raw);
  if (capped !== raw) {
    const suggest = $("nameSuggest");
    suggest.innerHTML = `Suggestion: <a href="#" onclick="applyNameCap(event,'${capped.replace(/'/g,"\\'")}')"><b>${capped}</b></a>`;
    suggest.classList.remove("hidden");
  }
});

function applyNameCap(e, capped) {
  e.preventDefault();
  $("name").value = capped;
  hide("nameSuggest");
  liveUpdate();
}


$("email").addEventListener("blur", () => {
  const v = val("email");
  if (v && !validateEmail(v)) show("emailError"); else hide("emailError");
});

$("phone").addEventListener("blur", () => {
  const v = val("phone");
  if (v && !validatePhone(v)) show("phoneError"); else hide("phoneError");
});


function liveUpdate() {
  setLastEdited();
  updatePreview();
  updateAnalytics();
}

function updatePreview() {
  const name = val("name") || "Your Name";
  const email = val("email");
  const phone = val("phone");
  const contact = [email, phone].filter(Boolean).join("  ·  ") || "email · phone";
  const summary = val("summary");

  $("pvName").textContent = name;
  $("pvContact").textContent = contact;

  if (summary) {
    show("pvSummaryBlock");
    $("pvSummary").textContent = summary;
  } else hide("pvSummaryBlock");

  if (state.experience.length) {
    show("pvExpBlock");
    $("pvExp").innerHTML = state.experience.map(e => `
      <div class="pv-exp-item">
        <div class="pv-exp-role">${e.role || "Role"}</div>
        <div class="pv-exp-meta">${[e.company, e.duration].filter(Boolean).join(" · ")}</div>
        ${e.description ? `<div class="pv-exp-desc">${e.description}</div>` : ""}
      </div>
    `).join("");
  } else hide("pvExpBlock");

  if (state.education.length) {
    show("pvEduBlock");
    $("pvEdu").innerHTML = state.education.map(e => `
      <div class="pv-edu-item">
        <div class="pv-edu-degree">${e.degree || "Degree"}</div>
        <div class="pv-edu-meta">${[e.institution, e.year].filter(Boolean).join(" · ")}</div>
      </div>
    `).join("");
  } else hide("pvEduBlock");

  if (state.skills.length) {
    show("pvSkillsBlock");
    $("pvSkills").innerHTML = state.skills.map(s => `<span class="pv-skill-tag">${s}</span>`).join("");
  } else hide("pvSkillsBlock");

  if (state.certifications.length) {
    show("pvCertBlock");
    $("pvCert").innerHTML = state.certifications.map(c => `• ${c}`).join("<br>");
  } else hide("pvCertBlock");

  if (state.languages.length) {
    show("pvLangBlock");
    $("pvLang").textContent = state.languages.join("  ·  ");
  } else hide("pvLangBlock");
}

function getFullText() {
  return [
    val("name"), val("email"), val("phone"), val("summary"),
    state.skills.join(" "),
    state.certifications.join(" "),
    state.languages.join(" "),
    ...state.experience.flatMap(e => [e.role, e.company, e.duration, e.description]),
    ...state.education.flatMap(e => [e.degree, e.institution, e.year]),
  ].filter(Boolean).join(" ");
}

function updateAnalytics() {
  const text = getFullText();
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const chars = text.length;
  const letters = text.replace(/[^\w\s]/g, "").length;
  const paras = [val("summary"), ...state.experience.map(e => e.description)].filter(p => p.trim()).length;
  const readTime = Math.ceil(words / 200);

  // Sidebar analytics
  $("aWords").textContent = words;
  $("aChars").textContent = chars;
  $("aLetters").textContent = letters;
  $("aParas").textContent = paras || 0;
  $("aRead").textContent = `~${readTime} min`;

  $("swWords").textContent = words;
  $("swChars").textContent = chars;
  $("swRead").textContent = `~${readTime}m`;
  $("swParas").textContent = paras || 0;
  $("swSkills").textContent = state.skills.length;
  $("swExp").textContent = state.experience.length;

  const pct = Math.min((words / 700) * 100, 100);
  const fill = $("wordRangeFill");
  fill.style.width = pct + "%";
  fill.style.background = words > 700 ? "var(--red)" : words >= 300 ? "var(--green)" : "var(--yellow)";

  const dpct = Math.min((words / 1000) * 100, 100);
  const df = $("densityFill");
  df.style.width = dpct + "%";
  df.style.background = words > 700 ? "var(--red)" : words >= 300 ? "var(--accent)" : "var(--yellow)";

  let status = "Start writing to see analysis";
  if (words > 0 && words < 300) status = `⚡ Too short — add ${300 - words} more words`;
  else if (words >= 300 && words <= 700) status = `✓ Ideal length (${words} / 700 words)`;
  else if (words > 700) status = `⚠ Over limit by ${words - 700} words`;
  $("densityStatus").textContent = status;

  if (words > 700) show("wordWarn"); else hide("wordWarn");
}


function setPreviewTab(name, btn) {
  document.querySelectorAll(".tab-content").forEach(t => t.classList.add("hidden"));
  document.querySelectorAll(".ptab").forEach(b => b.classList.remove("active"));
  $("tab" + name.charAt(0).toUpperCase() + name.slice(1)).classList.remove("hidden");
  btn.classList.add("active");
}


async function submitResume() {
  const sessRes = await fetch("/session-status");
  const sess = await sessRes.json();
  if (sess.expired) { show("sessionBanner"); return; }

  const name = val("name");
  const email = val("email");
  const fb = $("formBanner");

  if (!name || !email) {
    fb.textContent = "Name and email are required.";
    show("formBanner"); return;
  }
  if (!validateEmail(email)) {
    fb.textContent = "Please enter a valid email address.";
    show("formBanner"); return;
  }
  if (val("phone") && !validatePhone(val("phone"))) {
    fb.textContent = "Please enter a valid phone number.";
    show("formBanner"); return;
  }
  hide("formBanner");

  const payload = {
    name, email,
    phone: val("phone"),
    dob: val("dob"),
    summary: val("summary"),
    skills: state.skills,
    experience: state.experience.map(({ role, company, duration, description }) =>
      ({ role, company, duration, description })
    ),
    education: state.education.map(({ degree, institution, year }) =>
      ({ degree, institution, year })
    ),
    certifications: state.certifications,
    languages: state.languages,
  };

  const res = await fetch("/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  if (!res.ok) {
    fb.textContent = data.error || JSON.stringify(data.errors || "Submission failed.");
    show("formBanner"); return;
  }

  state.currentId = data.id;
  state.whatsappSent = false;
  state.flags = data.flags || {};

  $("resultId").textContent = data.id;

  const pwEl = $("resultPassword");
  if (data.password) {
    pwEl.innerHTML = `<code>${data.password}</code>`;
  } else {
    pwEl.textContent = "—";
  }

  const expDate = new Date(data.expires_at + "Z");
  $("resultExpiry").textContent = expDate.toLocaleString("en-IN");
  $("resultDownloads").textContent = "0";

  buildResultActions(data.flags || {});
  show("resultCard");
  hide("shareStatus");

  if (data.flags?.whatsapp) {
    show("waSection");
    $("waSentNote").style.display = "none";
  } else {
    hide("waSection");
  }
}

function buildResultActions(flags) {
  const container = $("resultActions");
  const actions = [];
  if (flags.download) {
    actions.push(`<button class="btn-secondary" onclick="downloadResume()">⬇ Download PDF</button>`);
  }
  if (flags.print) {
    actions.push(`<button class="btn-ghost" onclick="printResume()">🖨 Print</button>`);
  }
  if (flags.email) {
    actions.push(`<button class="btn-ghost" onclick="shareEmail()">✉ Email</button>`);
  }
  if (!actions.length) {
    actions.push(`<span style="font-size:12px;color:var(--muted)">Actions are disabled by admin.</span>`);
  }
  container.innerHTML = actions.join("");
}

async function downloadResume() {
  if (!state.currentId) return;
  window.open(`/resume/${state.currentId}/download`, "_blank");
  const cur = parseInt($("resultDownloads").textContent) || 0;
  $("resultDownloads").textContent = cur + 1;
}

function printResume() {
  if (!state.currentId) return;
  window.open(`/resume/${state.currentId}/download`, "_blank");
}

async function shareEmail() {
  if (!state.currentId) return;
  const email = val("email") || prompt("Enter recipient email:");
  if (!email) return;
  const res = await fetch(`/resume/${state.currentId}/share/email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json();
  const s = $("shareStatus");
  s.textContent = res.ok ? `✓ ${data.message}` : `✗ ${data.error}`;
  s.className = `banner ${res.ok ? "banner-success" : "banner-error"}`;
  show("shareStatus");
  setTimeout(() => hide("shareStatus"), 4000);
}

async function shareWhatsApp() {
  if (!state.currentId || state.whatsappSent) return;
  const phone = val("waPhone");
  const res = await fetch(`/resume/${state.currentId}/share/whatsapp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });
  const data = await res.json();
  if (res.ok) {
    window.open(data.link, "_blank");
    state.whatsappSent = true;
    $("waSentNote").style.display = "flex";
    $(".btn-wa") && ($(".btn-wa").disabled = true);
  } else {
    const s = $("shareStatus");
    s.textContent = `✗ ${data.error}`;
    s.className = "banner banner-error";
    show("shareStatus");
    setTimeout(() => hide("shareStatus"), 4000);
  }
}

// ── Session Timer ─────────────────────────────────────────────────────────────

function startTimer(remaining) {
  const timerEl = $("timer");
  const fillEl = $("timerFill");
  const TOTAL = 1200;

  function tick() {
    if (remaining <= 0) {
      timerEl.textContent = "00:00";
      timerEl.className = "timer critical";
      fillEl.style.width = "0%";
      show("sessionBanner");
      return;
    }
    const m = String(Math.floor(remaining / 60)).padStart(2, "0");
    const s = String(remaining % 60).padStart(2, "0");
    timerEl.textContent = `${m}:${s}`;
    fillEl.style.width = `${(remaining / TOTAL) * 100}%`;
    timerEl.className = "timer" + (remaining <= 60 ? " critical" : remaining <= 300 ? " warn" : "");
    remaining--;
    setTimeout(tick, 1000);
  }
  tick();
}

async function initTimer() {
  const res = await fetch("/session-status");
  const data = await res.json();
  if (data.expired) show("sessionBanner");
  startTimer(data.remaining_seconds);
}

async function loadFlags() {
  const res = await fetch("/flags");
  state.flags = await res.json();
}


initTimer();
loadFlags();
liveUpdate();
