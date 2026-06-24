const state = {
  data: null,
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

function render() {
  renderMeta();
  renderItems();
}

async function loadData() {
  elements.statusMessage.textContent = "데이터를 불러오는 중입니다.";
  elements.itemsList.innerHTML = "";

  try {
    const response = await fetch("./data.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    state.data = await response.json();
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
