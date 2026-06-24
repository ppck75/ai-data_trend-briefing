const state = {
  data: null,
  briefing: null,
  activeGroup: "all",
};

const groupLabels = {
  news: "뉴스",
  tech_blog: "기술블로그",
  ai_data: "AI·데이터",
};

const elements = {
  updatedAt: document.querySelector("#updatedAt"),
  totalItems: document.querySelector("#totalItems"),
  briefingSection: document.querySelector("#briefingSection"),
  briefingMethod: document.querySelector("#briefingMethod"),
  integratedTop5: document.querySelector("#integratedTop5"),
  newsTop5: document.querySelector("#newsTop5"),
  techTop5: document.querySelector("#techTop5"),
  aiTop5: document.querySelector("#aiTop5"),
  hotKeywords: document.querySelector("#hotKeywords"),
  statusMessage: document.querySelector("#statusMessage"),
  itemsList: document.querySelector("#itemsList"),
  refreshButton: document.querySelector("#refreshButton"),
  filterButtons: document.querySelectorAll(".filter-button"),
};

function parseDate(value) {
  if (!value) return 0;
  const time = Date.parse(value);
  return Number.isNaN(time) ? 0 : time;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getVisibleItems() {
  const items = [...(state.data?.items ?? [])];
  const filtered =
    state.activeGroup === "all"
      ? items
      : items.filter((item) => item.group === state.activeGroup);

  return filtered.sort((a, b) => {
    const aDate = parseDate(a.published_at || a.fetched_at);
    const bDate = parseDate(b.published_at || b.fetched_at);
    return bDate - aDate;
  });
}

function renderMeta() {
  elements.updatedAt.textContent = formatDate(state.data?.updated_at);
  elements.totalItems.textContent = state.data?.total_items ?? 0;
}

function renderItems() {
  const items = getVisibleItems();
  elements.itemsList.innerHTML = "";

  if (!items.length) {
    elements.statusMessage.textContent = "수집된 항목이 없습니다.";
    return;
  }

  elements.statusMessage.textContent = "";
  const fragment = document.createDocumentFragment();

  for (const item of items) {
    const article = document.createElement("article");
    article.className = "item-card";
    article.innerHTML = `
      <div class="item-icon" aria-hidden="true">${escapeHtml(item.icon || "•")}</div>
      <div class="item-content">
        <div class="item-meta">
          <span>${escapeHtml(item.source || "Unknown")}</span>
          <span>${escapeHtml(groupLabels[item.group] || item.group || "")}</span>
          <span>${escapeHtml(item.category || "")}</span>
        </div>
        <h2>${escapeHtml(item.title || "제목 없음")}</h2>
        <p class="item-summary">${escapeHtml(item.summary || "요약 없음")}</p>
        <div class="item-footer">
          <time datetime="${escapeHtml(item.published_at || "")}">
            ${escapeHtml(formatDate(item.published_at || item.fetched_at))}
          </time>
          <a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
        </div>
      </div>
    `;
    fragment.appendChild(article);
  }

  elements.itemsList.appendChild(fragment);
}

function renderIntegratedTop5() {
  const items = state.briefing?.integrated_top5 ?? [];
  elements.integratedTop5.innerHTML = "";
  elements.briefingMethod.textContent = state.briefing
    ? `${state.briefing.method}${state.briefing.fallback_used ? " + fallback" : ""}`
    : "-";

  if (!items.length) {
    elements.integratedTop5.innerHTML = '<p class="muted-text">통합 Top 5가 아직 생성되지 않았습니다.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const article = document.createElement("article");
    article.className = "briefing-card";
    article.innerHTML = `
      <div class="rank-badge">${escapeHtml(item.rank ?? "-")}</div>
      <div>
        <div class="item-meta">
          <span>${escapeHtml(item.source || "Unknown")}</span>
          <span>${escapeHtml(groupLabels[item.group] || item.group || "")}</span>
          <span>${escapeHtml(String(item.integrated_score ?? ""))}점</span>
        </div>
        <h3>${escapeHtml(item.title || "제목 없음")}</h3>
        <p>${escapeHtml(item.one_line_summary || item.summary || "")}</p>
        <p class="insight-text">${escapeHtml(item.planning_insight || "")}</p>
        <a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
      </div>
    `;
    fragment.appendChild(article);
  }
  elements.integratedTop5.appendChild(fragment);
}

function renderCategoryTop5(target, items) {
  target.innerHTML = "";
  if (!items?.length) {
    target.innerHTML = '<p class="muted-text">선정된 항목이 없습니다.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const row = document.createElement("article");
    row.className = "compact-item";
    row.innerHTML = `
      <strong>${escapeHtml(item.rank ?? "-")}. ${escapeHtml(item.title || "제목 없음")}</strong>
      <span>${escapeHtml(item.source || "")} · ${escapeHtml(String(item.category_score ?? ""))}점</span>
      <p>${escapeHtml(item.score_reason || "")}</p>
    `;
    fragment.appendChild(row);
  }
  target.appendChild(fragment);
}

function renderKeywords() {
  const keywords = state.briefing?.hot_keywords ?? [];
  elements.hotKeywords.innerHTML = "";
  if (!keywords.length) {
    elements.hotKeywords.innerHTML = '<p class="muted-text">키워드가 아직 생성되지 않았습니다.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const keyword of keywords) {
    const badge = document.createElement("span");
    badge.className = "keyword-badge";
    badge.textContent = `${keyword.keyword} ${keyword.count}`;
    fragment.appendChild(badge);
  }
  elements.hotKeywords.appendChild(fragment);
}

function renderBriefing() {
  if (!state.briefing) {
    elements.briefingSection.classList.add("is-empty");
    elements.briefingMethod.textContent = "briefing 없음";
    renderIntegratedTop5();
    renderCategoryTop5(elements.newsTop5, []);
    renderCategoryTop5(elements.techTop5, []);
    renderCategoryTop5(elements.aiTop5, []);
    renderKeywords();
    return;
  }

  elements.briefingSection.classList.remove("is-empty");
  renderIntegratedTop5();
  renderCategoryTop5(elements.newsTop5, state.briefing.category_top5?.news);
  renderCategoryTop5(elements.techTop5, state.briefing.category_top5?.tech_blog);
  renderCategoryTop5(elements.aiTop5, state.briefing.category_top5?.ai_data);
  renderKeywords();
}

function render() {
  renderMeta();
  renderBriefing();
  renderItems();
}

async function loadData() {
  elements.statusMessage.textContent = "데이터를 불러오는 중입니다.";
  elements.itemsList.innerHTML = "";

  try {
    const response = await fetch("./data.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`data.json HTTP ${response.status}`);
    }
    state.data = await response.json();

    try {
      const briefingResponse = await fetch("./briefing.json", { cache: "no-store" });
      state.briefing = briefingResponse.ok ? await briefingResponse.json() : null;
    } catch {
      state.briefing = null;
    }

    render();
  } catch (error) {
    elements.updatedAt.textContent = "-";
    elements.totalItems.textContent = "0";
    elements.statusMessage.textContent = `data.json 로드 실패: ${error.message}`;
  }
}

elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.activeGroup = button.dataset.group;
    elements.filterButtons.forEach((target) => target.classList.remove("active"));
    button.classList.add("active");
    renderItems();
  });
});

elements.refreshButton.addEventListener("click", loadData);

loadData();
