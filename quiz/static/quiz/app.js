(() => {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp;
  const inTelegram = !!(tg && tg.initData);
  const app = document.getElementById("app");
  const sheetRoot = document.getElementById("sheet-root");
  const toastEl = document.getElementById("toast");
  const tabbar = document.getElementById("tabbar");
  const qnav = document.getElementById("qnav");
  const TABS = ["home", "rank", "me"];
  const PERIODS = [["day", "Bugun"], ["week", "Hafta"], ["month", "Oy"]];
  const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const LETTERS = ["A", "B", "C", "D"];
  const FONT_STEPS = [1, 1.15, 1.3];

  const ICON = {
    chev: '<svg class="chev" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>',
    mix: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5"/><path d="M4 20L21 3"/><path d="M21 16v5h-5"/><path d="M15 15l6 6"/><path d="M4 4l5 5"/></svg>',
    doc: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 14l2 2 4-4"/></svg>',
    play: '<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5z"/></svg>',
    close: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    check: '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    cross: '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M7 7l10 10M17 7L7 17"/></svg>',
    checkSm: '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  };

  const state = { home: null, session: null, question: null, last: null, busy: false, screen: "", sheet: null,
    rank: null, me: null, period: "week" };

  // ------------------------------------------------------------ yordamchilar
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* xotira yopiq bo'lishi mumkin */ } },
  };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

  function haptic(type) {
    try { if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(type); } catch (e) { /* eski versiya */ }
  }

  let toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3200);
  }

  function confirmBox(msg) {
    return new Promise((resolve) => {
      if (tg && tg.showConfirm && tg.isVersionAtLeast && tg.isVersionAtLeast("6.2")) tg.showConfirm(msg, resolve);
      else resolve(window.confirm(msg));
    });
  }

  async function api(path, body) {
    const opt = { method: body ? "POST" : "GET", headers: {} };
    if (inTelegram) opt.headers.Authorization = "tma " + tg.initData;
    if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
    let res;
    try { res = await fetch("api/" + path, opt); } catch (e) { throw new Error("net"); }
    if (res.status === 401 || res.status === 403) throw new Error("auth");
    if (!res.ok) throw new Error("server");
    return res.json();
  }

  function fail(e) {
    if (e.message === "auth") return notice(
      inTelegram ? "Sessiya eskirdi" : "Telegram orqali oching",
      inTelegram ? "Ilovani yopib, qaytadan oching." : "Bu sahifa faqat Telegram bot ichida ishlaydi.");
    toast(e.message === "net" ? "Internet aloqasi yo‘q. Qayta urinib ko‘ring." : "Xatolik yuz berdi. Qayta urinib ko‘ring.");
  }

  function notice(title, text) {
    setScreen("notice");
    app.innerHTML = `<div class="screen notice"><h2>${esc(title)}</h2><p>${esc(text)}</p></div>`;
  }

  // ------------------------------------------------------------ ko'rinish sozlamalari
  function applyTheme() {
    const dark = tg && tg.colorScheme ? tg.colorScheme === "dark"
      : window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
    try { if (tg && tg.setHeaderColor) tg.setHeaderColor(bg); if (tg && tg.setBackgroundColor) tg.setBackgroundColor(bg); } catch (e) { /* eski versiya */ }
  }

  function applyFont(step) {
    document.documentElement.style.setProperty("--fs", FONT_STEPS[step]);
  }

  function setScreen(name) {
    state.screen = name;
    const tabs = TABS.includes(name);
    tabbar.hidden = !tabs;
    qnav.hidden = name !== "quiz";
    document.body.classList.toggle("has-qnav", name === "quiz");
    document.body.classList.toggle("has-tabs", tabs);
    tabbar.querySelectorAll("button").forEach((b) => {
      if (b.dataset.tab === name) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    if (!tg) return;
    try {
      if (name === "quiz" || name === "result") tg.BackButton.show(); else tg.BackButton.hide();
      if (name === "quiz") tg.enableClosingConfirmation(); else tg.disableClosingConfirmation();
    } catch (e) { /* eski versiya */ }
  }

  function loading() {
    app.innerHTML = '<div class="loading"><span class="spinner"></span></div>';
  }

  // ------------------------------------------------------------ bosh sahifa
  async function showHome() {
    setScreen("home");
    if (!state.home) loading();
    try { state.home = await api("home/"); } catch (e) { return fail(e); }
    if (state.screen !== "home") return;
    renderHome();
  }

  function renderHome() {
    const h = state.home;
    const topicCount = h.modules.reduce((n, m) => n + m.topics.length, 0);
    const resume = h.resume ? `
      <button class="hero resume" data-act="resume">
        <span class="ico">${ICON.play}</span>
        <span class="tx"><b>Davom ettirish</b><small>${esc(h.resume.title)} · ${h.resume.position} / ${h.resume.total}</small></span>
        ${ICON.chev}
      </button>` : "";
    const exam = h.exam ? `
      <button class="hero exam" data-act="exam">
        <span class="ico">${ICON.doc}</span>
        <span class="tx"><b>${esc(h.exam.title)}</b><small>Imtihonda tushgan savollar · ${h.exam.count} ta</small></span>
        ${ICON.chev}
      </button>` : "";
    const modules = h.modules.map((m) => `
      <section class="module">
        <h2><small>${m.number}-modul</small>${esc(m.title)}</h2>
        <div class="list">${m.topics.map((t) => `
          <button class="row" data-act="topic" data-id="${t.id}">
            <span class="code">${esc(t.code)}</span>
            <span class="t">${esc(t.title)}<small>${t.count} ta savol</small></span>
            ${t.best === null || t.best === undefined ? ICON.chev : `<span class="best">${t.best}%</span>`}
          </button>`).join("")}
        </div>
      </section>`).join("");

    app.innerHTML = `
      <div class="screen">
        <header class="top">
          <div><h1>Testlar</h1><p>${topicCount} ta mavzu · ${h.total} ta savol</p></div>
          <button class="fs-btn" data-act="font" aria-label="Harf o‘lchamini o‘zgartirish"><small>A</small>A</button>
        </header>
        ${resume}
        ${exam}
        <button class="hero" data-act="mixed">
          <span class="ico">${ICON.mix}</span>
          <span class="tx"><b>Aralash test</b><small>Barcha mavzulardan</small></span>
          ${ICON.chev}
        </button>
        ${modules}
      </div>`;
  }

  // ------------------------------------------------------------ reyting
  const level = (p) => (p >= 85 ? "" : p >= 60 ? " mid" : " low");

  async function showRank(period) {
    if (period && period !== state.period) {
      state.period = period;
      store.set("period", period);
      state.rank = null;
    }
    setScreen("rank");
    renderRank();
    window.scrollTo(0, 0);
    let r;
    try { r = await api("leaderboard/?period=" + state.period); } catch (e) { return fail(e); }
    if (state.screen !== "rank" || r.period !== state.period) return;
    state.rank = r;
    renderRank();
  }

  function rankRow(e) {
    return `
      <div class="rrow${e.me ? " me" : ""}">
        <span class="rk${e.rank <= 3 ? " r" + e.rank : ""}">${e.rank}</span>
        <span class="t">${esc(e.name)}${e.me ? " <em>(siz)</em>" : ""}<small>${e.percent}% to‘g‘ri</small></span>
        <span class="num"><b>${e.answered}</b><small>savol</small></span>
      </div>`;
  }

  function renderRank() {
    const r = state.rank;
    const seg = PERIODS.map(([k, label]) =>
      `<button data-act="period" data-period="${k}" aria-pressed="${k === state.period}">${label}</button>`).join("");
    let body;
    if (!r) body = '<div class="loading small"><span class="spinner"></span></div>';
    else if (!r.top.length) body = '<p class="empty">Bu davrda hali hech kim test ishlamadi.<br>Birinchi bo‘ling!</p>';
    else {
      const outside = r.me && r.me.rank > r.top.length;
      body = `<div class="list">${r.top.map(rankRow).join("")}${outside ? '<div class="gap">···</div>' + rankRow(r.me) : ""}</div>`
        + (r.me ? "" : '<p class="empty">Siz bu davrda hali test ishlamadingiz.</p>');
    }
    app.innerHTML = `
      <div class="screen">
        <header class="top"><div><h1>Reyting</h1><p>Eng ko‘p savol ishlaganlar</p></div></header>
        <div class="seg">${seg}</div>
        ${body}
      </div>`;
  }

  // ------------------------------------------------------------ mening natijalarim
  function fmtDate(iso) {
    const d = new Date(iso);
    const two = (n) => String(n).padStart(2, "0");
    return `${d.getDate()}-${MONTHS[d.getMonth()]}, ${two(d.getHours())}:${two(d.getMinutes())}`;
  }

  async function showMe() {
    setScreen("me");
    if (state.me) renderMe(); else loading();
    window.scrollTo(0, 0);
    let r;
    try { r = await api("me/"); } catch (e) { return fail(e); }
    if (state.screen !== "me") return;
    state.me = r;
    renderMe();
  }

  function renderMe() {
    const m = state.me;
    const recent = m.recent.length ? `
      <section class="module">
        <h2>Oxirgi testlar</h2>
        <div class="list">${m.recent.map((s) => `
          <div class="row static">
            <span class="t">${esc(s.title)}
              <small>${fmtDate(s.date)} · ${s.mode === "exam" ? "Imtihon" : "Mashq"} · ${s.correct} / ${s.answered}${s.active ? " · tugallanmagan" : ""}</small></span>
            <span class="best${level(s.percent)}">${s.percent}%</span>
          </div>`).join("")}
        </div>
      </section>` : '<p class="empty">Hali test ishlamadingiz.<br>«Testlar» bo‘limidan boshlang.</p>';
    app.innerHTML = `
      <div class="screen">
        <header class="top"><div><h1>Natijalarim</h1><p>${esc(m.name || "")}</p></div></header>
        <div class="stats">
          <div class="stat"><b>${m.today.answered}</b><span>Bugun</span></div>
          <div class="stat"><b>${m.week.answered}</b><span>Shu hafta</span></div>
          <div class="stat"><b>${m.all.answered}</b><span>Jami savol</span></div>
          <div class="stat ok"><b>${m.all.percent}%</b><span>To‘g‘ri javob</span></div>
        </div>
        ${recent}
      </div>`;
  }

  // ------------------------------------------------------------ boshlash oynasi
  function openSheet(topic) {
    const max = topic ? topic.count : state.home.total;
    const saved = parseInt(store.get("mixedCount", "30"), 10) || 30;
    const sheet = {
      topic,
      max,
      count: topic ? max : clamp(saved, 1, max),
      mode: store.get("mode", "strict") === "exam" ? "exam" : "strict",
    };
    state.sheet = sheet;
    const presets = (topic ? [10, 20, 30] : [10, 20, 30, 50, 100]).filter((n) => n < max);
    const chips = presets.map((n) => `<button class="chip" data-count="${n}">${n}</button>`).join("")
      + `<button class="chip" data-count="${max}">${topic ? "Hammasi" : "Hammasi (" + max + ")"}</button>`;

    sheetRoot.innerHTML = `
      <div class="overlay" data-act="sheet-close">
        <div class="sheet" role="dialog" aria-modal="true">
          <div class="grab"></div>
          <h3>${esc(topic ? topic.title : "Aralash test")}</h3>
          <p class="sub">${topic ? (topic.exam ? "Imtihonda tushgan savollar" : esc(topic.code) + "-mavzu") + " · " + max + " ta savol" : "Barcha mavzulardan aralash savollar"}</p>

          <p class="label">Savollar soni</p>
          <div class="stepper">
            <button data-step="-5" aria-label="Kamaytirish">−</button>
            <input id="cnt" type="number" inputmode="numeric" min="1" max="${max}" value="${sheet.count}" aria-label="Savollar soni">
            <button data-step="5" aria-label="Ko‘paytirish">+</button>
          </div>
          <div class="chips">${chips}</div>

          <p class="label">Rejim</p>
          <div class="modes" role="radiogroup">
            <button class="mode" role="radio" data-mode="strict">
              <span class="radio"></span>
              <span class="tx"><b>Mashq</b><small>To‘g‘ri javobni topguncha davom etadi</small></span>
            </button>
            <button class="mode" role="radio" data-mode="exam">
              <span class="radio"></span>
              <span class="tx"><b>Imtihon</b><small>Har bir savolga bitta urinish</small></span>
            </button>
          </div>

          <button class="btn" data-act="start">Boshlash</button>
        </div>
      </div>`;
    syncSheet();
    try { if (tg) tg.BackButton.show(); } catch (e) { /* eski versiya */ }
  }

  // "Tushgan testlar"da bir nechta to'plam bo'lsa — avval qaysi biri ekanini tanlash oynasi
  function openChooser(group) {
    state.sheet = { chooser: true };
    sheetRoot.innerHTML = `
      <div class="overlay">
        <div class="sheet" role="dialog" aria-modal="true">
          <div class="grab"></div>
          <h3>${esc(group.title)}</h3>
          <p class="sub">Qaysi to‘plamni ishlaysiz?</p>
          <div class="list pick">${group.topics.map((t) => `
            <button class="row" data-pick="${t.id}">
              <span class="t">${esc(t.title)}<small>${t.count} ta savol</small></span>
              ${t.best === null || t.best === undefined ? ICON.chev : `<span class="best">${t.best}%</span>`}
            </button>`).join("")}
          </div>
        </div>
      </div>`;
    try { if (tg) tg.BackButton.show(); } catch (e) { /* eski versiya */ }
  }

  function findTopic(id) {
    const h = state.home;
    const all = h.modules.flatMap((m) => m.topics).concat(h.exam ? h.exam.topics : []);
    return all.find((t) => t.id === id);
  }

  function syncSheet() {
    const s = state.sheet;
    if (!s || s.chooser) return;
    const input = sheetRoot.querySelector("#cnt");
    if (input && document.activeElement !== input) input.value = s.count;
    sheetRoot.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(+c.dataset.count === s.count)));
    sheetRoot.querySelectorAll(".mode").forEach((m) => m.setAttribute("aria-checked", String(m.dataset.mode === s.mode)));
  }

  function closeSheet() {
    const overlay = sheetRoot.querySelector(".overlay");
    state.sheet = null;
    if (state.screen === "home") { try { if (tg) tg.BackButton.hide(); } catch (e) { /* eski versiya */ } }
    if (!overlay) return;
    overlay.classList.add("closing");
    setTimeout(() => { if (!state.sheet) sheetRoot.innerHTML = ""; }, 200);
  }

  async function start(params, button) {
    if (state.busy) return;
    state.busy = true;
    if (button) button.disabled = true;
    try {
      const r = await api("sessions/", params);
      state.last = params;
      store.set("mode", params.mode);
      if (!params.topic) store.set("mixedCount", String(params.count));
      closeSheet();
      openQuiz(r);
    } catch (e) {
      if (button) button.disabled = false;
      fail(e);
    } finally {
      state.busy = false;
    }
  }

  async function resume(id) {
    loading();
    try {
      const r = await api(`sessions/${id}/`);
      state.last = null;
      if (r.session.done || !r.question) { state.session = r.session; return showResult(); }
      openQuiz(r);
    } catch (e) { fail(e); showHome(); }
  }

  // ------------------------------------------------------------ test
  const qcache = new Map(); // index -> savol holati (oldingi/keyingi savolga tez o'tish uchun)

  function setQuestion(q) {
    state.question = q;
    qcache.set(q.index, q);
  }

  function openQuiz(r) {
    qcache.clear();
    state.session = r.session;
    setQuestion(r.question);
    renderQuiz();
  }

  function renderQuiz() {
    setScreen("quiz");
    const s = state.session;
    app.innerHTML = `
      <div class="screen">
        <div class="qbar">
          <button class="close" data-act="exit" aria-label="Chiqish">${ICON.close}</button>
          <div class="count"><span id="pos"></span> <small>/ ${s.total}</small></div>
          <span class="spacer"></span>
        </div>
        <div class="progress"><i id="bar"></i></div>
        <div class="qwrap" id="qwrap"></div>
      </div>`;
    renderQuestion("");
    window.scrollTo(0, 0);
  }

  function explHtml(q) {
    return q.explanation ? `<div class="expl"><b>Izoh</b><p>${esc(q.explanation)}</p></div>` : "";
  }

  // dir: "" (animatsiyasiz) | "fwd" | "back"
  function renderQuestion(dir) {
    const q = state.question;
    const exam = state.session.mode === "exam";
    const wrap = document.getElementById("qwrap");
    wrap.className = "qwrap" + (dir ? " enter-" + dir : "");
    wrap.innerHTML = `
      ${q.topic ? `<p class="qtopic">${esc(q.topic)}</p>` : ""}
      <div class="qtext${q.text.includes("
") || q.text.length > 320 ? " long" : ""}">${esc(q.text)}</div>
      <div class="opts">${q.options.map((o, i) => {
        let cls = "", mark = "";
        if (q.tried.includes(i)) { cls = " wrong"; mark = ICON.cross; }
        else if (q.answered && i === q.correct_position) {
          cls = (exam && q.tried.length ? " reveal" : " correct") + " still";
          mark = ICON.check;
        } else if (q.answered) cls = " dim";
        return `<button class="opt${cls}" data-pos="${i}"${q.answered || q.tried.includes(i) ? " disabled" : ""}>
          <span class="ltr">${LETTERS[i]}</span><span class="txt">${esc(o)}</span>
          <span class="mark">${mark}</span></button>`;
      }).join("")}</div>
      <p class="hint" id="hint"></p>
      <div id="expl">${q.answered ? explHtml(q) : ""}</div>`;
    updateBar();
  }

  function updateBar() {
    const s = state.session, q = state.question;
    const pos = document.getElementById("pos");
    const bar = document.getElementById("bar");
    if (pos) pos.textContent = q.index + 1;
    if (bar) bar.style.width = (100 * s.position) / s.total + "%";
    const prev = qnav.querySelector('[data-nav="prev"]');
    const next = qnav.querySelector('[data-nav="next"]');
    prev.disabled = q.index === 0;
    document.getElementById("nextLabel").textContent = s.done ? "Natija" : "Keyingi";
    // savolga javob berilgan bo'lsa "Keyingi" asosiy (to'q) tugma bo'ladi
    next.classList.toggle("ghost", !q.answered && !s.done);
  }

  function setMark(btn, kind) {
    btn.classList.add(kind);
    btn.querySelector(".mark").innerHTML = kind === "wrong" ? ICON.cross : ICON.check;
  }

  function shake(btn) {
    btn.classList.remove("shake");
    void btn.offsetWidth; // animatsiyani qayta boshlash
    btn.classList.add("shake");
  }

  function prefetch(index) {
    const s = state.session;
    if (index < 0 || index >= s.total || qcache.has(index)) return;
    api(`sessions/${s.id}/q/${index}/`).then((r) => {
      if (state.session && state.session.id === s.id && !qcache.has(index)) qcache.set(index, r.question);
    }).catch(() => { /* keyin kerak bo'lganda qayta so'raladi */ });
  }

  async function goTo(index, dir) {
    const s = state.session;
    if (state.busy || index < 0 || index >= s.total || index === state.question.index) return;
    state.busy = true;
    let q = qcache.get(index);
    if (!q) {
      try {
        const r = await api(`sessions/${s.id}/q/${index}/`);
        q = r.question;
        state.session = r.session;
      } catch (e) { state.busy = false; return fail(e); }
    }
    const wrap = document.getElementById("qwrap");
    if (wrap) wrap.classList.add("leave-" + dir);
    await sleep(170);
    if (state.screen !== "quiz") { state.busy = false; return; }
    setQuestion(q);
    renderQuestion(dir);
    window.scrollTo(0, 0);
    state.busy = false;
    prefetch(index + (dir === "back" ? -1 : 1));
  }

  function goNext() {
    const s = state.session, q = state.question;
    if (state.busy) return;
    if (s.done) return showResult();
    if (q.index + 1 < s.total) return goTo(q.index + 1, "fwd");
    // oxirgi savol, lekin javob berilmaganlari qolgan
    toast(`Javob berilmagan savollar: ${s.total - s.position} ta`);
    if (s.current !== null && s.current !== q.index) goTo(s.current, "back");
  }

  async function choose(btn) {
    if (state.busy || btn.disabled) return;
    const q = state.question;
    const pos = +btn.dataset.pos;
    state.busy = true;
    btn.classList.add("pending");

    let r;
    try {
      r = await api(`sessions/${state.session.id}/answer/`, { index: q.index, position: pos });
    } catch (e) {
      btn.classList.remove("pending");
      state.busy = false;
      return fail(e);
    }
    btn.classList.remove("pending");
    state.session = r.session;
    if (state.screen !== "quiz" || state.question.index !== q.index) { state.busy = false; return; }
    if (r.question) setQuestion(r.question);

    if (r.stale || !r.question) { // holat serverdagidan orqada qolgan — tenglashtiramiz
      if (r.question) renderQuestion("");
      state.busy = false;
      return;
    }

    const all = [...document.querySelectorAll(".opt")];
    const hint = document.getElementById("hint");

    if (!r.resolved) { // mashq rejimi, xato: to'g'risini ko'rsatmaymiz, savol ochiq qoladi
      setMark(btn, "wrong");
      shake(btn);
      haptic("error");
      btn.disabled = true;
      hint.textContent = "Xato. Yana urinib ko‘ring";
      hint.className = "hint show";
      state.busy = false;
      return;
    }

    all.forEach((b) => { b.disabled = true; });
    if (r.correct) {
      setMark(btn, "correct");
      hint.textContent = "To‘g‘ri!";
      hint.className = "hint ok show";
      haptic("success");
    } else { // imtihon rejimi, xato: to'g'ri javob ham ko'rsatiladi
      setMark(btn, "wrong");
      shake(btn);
      haptic("error");
      const right = all[r.question.correct_position];
      if (right) setMark(right, "reveal");
    }
    all.forEach((b) => {
      if (!["wrong", "correct", "reveal"].some((c) => b.classList.contains(c))) b.classList.add("dim");
    });
    updateBar();
    prefetch(q.index + 1);

    if (r.question.explanation) { // izoh bor — foydalanuvchi o'qib, "Keyingi"ni o'zi bosadi
      const box = document.getElementById("expl");
      box.innerHTML = explHtml(r.question);
      state.busy = false;
      await sleep(350);
      const el = box.firstElementChild;
      if (el && el.isConnected) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    // izoh yo'q — avvalgidek o'zi keyingi savolga o'tadi
    await sleep(r.correct ? 800 : 1700);
    state.busy = false;
    if (state.screen !== "quiz" || state.question.index !== q.index) return;
    if (r.session.done) return showResult();
    if (q.index + 1 < r.session.total) goTo(q.index + 1, "fwd");
  }

  async function exitQuiz() {
    if (state.busy) return;
    const s = state.session;
    if (s && s.position > 0 && !s.done && !(await confirmBox("Testdan chiqasizmi? Keyin davom ettirishingiz mumkin."))) return;
    showHome();
  }

  // ------------------------------------------------------------ natija
  async function showResult() {
    setScreen("result");
    loading();
    let r;
    try { r = await api(`sessions/${state.session.id}/result/`); } catch (e) { fail(e); return showHome(); }
    if (state.screen !== "result") return;
    state.home = null; // bosh sahifa va reyting yangilansin
    state.rank = null;

    const p = r.percent;
    const level = p >= 85 ? "" : p >= 60 ? "mid" : "low";
    const title = p >= 85 ? "Ajoyib natija!" : p >= 60 ? "Yaxshi natija" : "Yana mashq qiling";
    const C = 2 * Math.PI * 52;
    const mistakes = r.mistakes.length ? `
      <section class="mistakes">
        <h3>Xato qilingan savollar</h3>
        ${r.mistakes.map((m) => `
          <div class="mistake"><p>${esc(m.text)}</p>
            <div class="ans">${ICON.checkSm}<span>${esc(m.correct)}</span></div>
            ${m.explanation ? `<p class="why">${esc(m.explanation)}</p>` : ""}</div>`).join("")}
      </section>` : "";

    app.innerHTML = `
      <div class="screen result">
        <div class="ring ${level}">
          <svg viewBox="0 0 120 120"><circle class="bg" cx="60" cy="60" r="52"/>
            <circle class="fg" id="ring" cx="60" cy="60" r="52" stroke-dasharray="${C}" stroke-dashoffset="${C}"/></svg>
          <div class="pct"><span id="pct">0%</span></div>
        </div>
        <h2>${title}</h2>
        <p class="sub">${esc(r.session.title)}</p>
        <div class="stats">
          <div class="stat ok"><b>${r.correct}</b><span>To‘g‘ri</span></div>
          <div class="stat bad"><b>${r.wrong}</b><span>Xato</span></div>
        </div>
        <div class="actions">
          <button class="btn" data-act="again">Yana bir bor</button>
          <button class="btn ghost" data-act="home">Bosh sahifa</button>
        </div>
        ${mistakes}
      </div>`;
    window.scrollTo(0, 0);
    haptic(p >= 60 ? "success" : "warning");

    requestAnimationFrame(() => requestAnimationFrame(() => {
      const ring = document.getElementById("ring");
      if (ring) ring.style.strokeDashoffset = C * (1 - p / 100);
    }));
    const pct = document.getElementById("pct");
    const t0 = performance.now();
    (function tick(now) {
      const k = Math.min(1, (now - t0) / 1000);
      if (!pct.isConnected) return;
      pct.textContent = Math.round(p * (1 - Math.pow(1 - k, 3))) + "%";
      if (k < 1) requestAnimationFrame(tick);
    })(t0);
  }

  function again() {
    const s = state.session;
    start(state.last || { topic: s.mixed ? null : s.topic, mode: s.mode, count: s.total });
  }

  // ------------------------------------------------------------ hodisalar
  app.addEventListener("click", (e) => {
    const opt = e.target.closest(".opt");
    if (opt) return choose(opt);
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const act = el.dataset.act;
    if (act === "topic") {
      const t = findTopic(+el.dataset.id);
      if (t) openSheet(t);
    } else if (act === "exam") {
      const group = state.home.exam;
      if (group.topics.length === 1) openSheet(group.topics[0]); else openChooser(group);
    } else if (act === "mixed") openSheet(null);
    else if (act === "resume") resume(state.home.resume.id);
    else if (act === "font") {
      const step = (parseInt(store.get("font", "0"), 10) + 1) % FONT_STEPS.length;
      store.set("font", String(step));
      applyFont(step);
    } else if (act === "exit") exitQuiz();
    else if (act === "home") showHome();
    else if (act === "again") again();
    else if (act === "period") showRank(el.dataset.period);
  });

  qnav.addEventListener("click", (e) => {
    const b = e.target.closest("[data-nav]");
    if (!b || b.disabled || state.screen !== "quiz") return;
    if (b.dataset.nav === "prev") goTo(state.question.index - 1, "back");
    else goNext();
  });

  tabbar.addEventListener("click", (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b || state.busy) return;
    if (b.dataset.tab === "rank") showRank();
    else if (b.dataset.tab === "me") showMe();
    else showHome();
  });

  sheetRoot.addEventListener("click", (e) => {
    const s = state.sheet;
    if (!s) return;
    if (e.target.classList.contains("overlay")) return closeSheet();
    const pick = e.target.closest("[data-pick]");
    if (pick) { const t = findTopic(+pick.dataset.pick); if (t) openSheet(t); return; }
    if (s.chooser) return;
    const step = e.target.closest("[data-step]");
    const chip = e.target.closest(".chip");
    const mode = e.target.closest(".mode");
    const go = e.target.closest('[data-act="start"]');
    if (step) {
      const d = +step.dataset.step;
      // 5 ga karrali songa "yopishadi": 30 -> 35, 33 -> 35, 33 -> 30
      const n = d > 0 ? Math.floor(s.count / 5) * 5 + 5 : Math.ceil(s.count / 5) * 5 - 5;
      s.count = clamp(n, 1, s.max);
    } else if (chip) s.count = +chip.dataset.count;
    else if (mode) s.mode = mode.dataset.mode;
    else if (go) {
      return start({ topic: s.topic ? s.topic.id : null, mode: s.mode, count: clamp(s.count || 1, 1, s.max) }, go);
    } else return;
    syncSheet();
  });

  sheetRoot.addEventListener("input", (e) => {
    const s = state.sheet;
    if (!s || e.target.id !== "cnt") return;
    const n = parseInt(e.target.value, 10);
    s.count = Number.isFinite(n) ? clamp(n, 1, s.max) : 1;
    syncSheet();
  });
  sheetRoot.addEventListener("change", (e) => {
    if (state.sheet && e.target.id === "cnt") e.target.value = state.sheet.count;
  });

  function onBack() {
    if (state.sheet) closeSheet();
    else if (state.screen === "quiz") exitQuiz();
    else if (state.screen === "result") showHome();
  }

  // ------------------------------------------------------------ ishga tushirish
  applyFont(clamp(parseInt(store.get("font", "0"), 10) || 0, 0, FONT_STEPS.length - 1));
  applyTheme();
  state.period = PERIODS.some(([k]) => k === store.get("period", "week")) ? store.get("period", "week") : "week";
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      tg.onEvent("themeChanged", applyTheme);
      tg.BackButton.onClick(onBack);
    } catch (e) { /* Telegram'dan tashqarida */ }
  }
  showHome();
})();
