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

  if (!items.length) {
    elements.integratedTop5.innerHTML = '<p class="muted-text">통합 Top 5가 아직 생성되지 않았습니다.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const article = document.createElement("article");
    article.className = "briefing-card";
    article.setAttribute("role", "button");
    article.setAttribute("tabindex", "0");
    article.setAttribute("aria-expanded", "false");
    article.innerHTML = `
      <div class="rank-badge">${escapeHtml(item.rank ?? "-")}</div>
      <div class="briefing-card-body">
        <div class="item-meta">
          <span>${escapeHtml(item.source || "Unknown")}</span>
          <span>${escapeHtml(groupLabels[item.group] || item.group || "")}</span>
        </div>
        <h3>${escapeHtml(item.title || "제목 없음")}</h3>
        <div class="briefing-details">
          <div class="briefing-field">
            <span>원문 요약</span>
            <p>${escapeHtml(item.one_line_summary || item.summary || "요약 없음")}</p>
          </div>
          <div class="briefing-field">
            <span>선정 이유</span>
            <p>${escapeHtml(item.importance_reason || item.score_reason || "선정 이유 없음")}</p>
          </div>
          <div class="briefing-field">
            <span>기획 인사이트</span>
            <p class="insight-text">${escapeHtml(item.planning_insight || "기획 인사이트 없음")}</p>
          </div>
          <div class="card-actions">
            <a class="source-button" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
          </div>
        </div>
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
      <span>${escapeHtml(item.source || "")}</span>
      <div class="briefing-field compact-field">
        <span>선정 이유</span>
        <p class="clampable">${escapeHtml(item.score_reason || "선정 이유 없음")}</p>
      </div>
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

document.addEventListener("click", (event) => {
  const sourceLink = event.target.closest(".source-button");
  if (sourceLink) return;

  const card = event.target.closest(".briefing-card");
  if (!card) return;

  const isExpanded = card.classList.toggle("expanded");
  card.setAttribute("aria-expanded", String(isExpanded));
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest(".briefing-card");
  if (!card) return;
  event.preventDefault();
  const isExpanded = card.classList.toggle("expanded");
  card.setAttribute("aria-expanded", String(isExpanded));
});

loadData();
