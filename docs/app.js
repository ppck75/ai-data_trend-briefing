const state = {
  data: null,
  briefing: null,
  archiveIndex: null,
  selectedArchiveDate: "",
  selectedArchiveId: "",
  activeGroup: null,
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
  archiveDateSelect: document.querySelector("#archiveDateSelect"),
  archiveTimeSelect: document.querySelector("#archiveTimeSelect"),
  archiveStatus: document.querySelector("#archiveStatus"),
  archiveViewer: document.querySelector("#archiveViewer"),
  statusMessage: document.querySelector("#statusMessage"),
  itemsList: document.querySelector("#itemsList"),
  refreshButton: document.querySelector("#refreshButton"),
  filterButtons: document.querySelectorAll(".filter-button"),
};

function setText(element, value) {
  if (element) {
    element.textContent = value;
  }
}

function setHtml(element, value) {
  if (element) {
    element.innerHTML = value;
  }
}

function clearElement(element) {
  setHtml(element, "");
}

function appendTo(element, child) {
  if (element) {
    element.appendChild(child);
  }
}

function showStatus(message) {
  setText(elements.statusMessage, message);
  elements.statusMessage?.classList.remove("is-hidden");
}

function hideStatus() {
  setText(elements.statusMessage, "");
  elements.statusMessage?.classList.add("is-hidden");
}

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
  if (!state.activeGroup) return [];
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
  setText(elements.updatedAt, formatDate(state.data?.updated_at));
  setText(elements.totalItems, state.data?.total_items ?? 0);
}

function renderItems() {
  const items = getVisibleItems();
  clearElement(elements.itemsList);

  if (!state.activeGroup) {
    showStatus("아래 탭을 선택하면 최신 RSS 원자료 목록이 표시됩니다.");
    return;
  }

  if (!items.length) {
    showStatus("수집된 항목이 없습니다.");
    return;
  }

  hideStatus();
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

  appendTo(elements.itemsList, fragment);
}

function renderIntegratedTop5() {
  const items = state.briefing?.integrated_top5 ?? [];
  clearElement(elements.integratedTop5);

  if (!items.length) {
    setHtml(elements.integratedTop5, '<p class="muted-text">통합 Top 5가 아직 생성되지 않았습니다.</p>');
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const article = document.createElement("article");
    article.className = "briefing-card";
    article.innerHTML = `
      <div class="rank-badge">${escapeHtml(item.rank ?? "-")}</div>
      <div class="briefing-card-body">
        <div class="item-meta">
          <span>${escapeHtml(item.source || "Unknown")}</span>
          <span>${escapeHtml(groupLabels[item.group] || item.group || "")}</span>
        </div>
        <h3>${escapeHtml(item.title || "제목 없음")}</h3>
        <div class="briefing-field">
          <span>선정 이유</span>
          <p class="clampable">${escapeHtml(item.importance_reason || item.score_reason || "선정 이유 없음")}</p>
        </div>
        <div class="card-actions">
          <a class="source-button" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
        </div>
      </div>
    `;
    fragment.appendChild(article);
  }
  appendTo(elements.integratedTop5, fragment);
}

function renderCategoryTop5(target, items) {
  clearElement(target);
  if (!items?.length) {
    setHtml(target, '<p class="muted-text">선정된 항목이 없습니다.</p>');
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
      <div class="card-actions">
        <a class="source-button secondary" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
      </div>
    `;
    fragment.appendChild(row);
  }
  appendTo(target, fragment);
}

function getArchiveDates() {
  const archives = state.archiveIndex?.archives ?? [];
  return [...new Set(archives.map((item) => item.date).filter(Boolean))].sort().reverse();
}

function getArchivesForDate(date) {
  return (state.archiveIndex?.archives ?? [])
    .filter((item) => item.date === date)
    .sort((a, b) => String(b.time).localeCompare(String(a.time)));
}

function renderArchiveControls() {
  const dates = getArchiveDates();
  clearElement(elements.archiveDateSelect);
  clearElement(elements.archiveTimeSelect);

  if (!dates.length) {
    if (elements.archiveDateSelect) {
      elements.archiveDateSelect.disabled = true;
      elements.archiveDateSelect.appendChild(new Option("저장된 날짜 없음", ""));
    }
    if (elements.archiveTimeSelect) {
      elements.archiveTimeSelect.disabled = true;
      elements.archiveTimeSelect.appendChild(new Option("저장된 시간 없음", ""));
    }
    setText(elements.archiveStatus, "저장된 지난 브리핑이 아직 없습니다. 예약 실행 후 07:35, 12:35, 17:35 브리핑이 여기에 누적됩니다.");
    clearElement(elements.archiveViewer);
    return;
  }

  if (elements.archiveDateSelect) {
    elements.archiveDateSelect.disabled = false;
  }
  if (elements.archiveTimeSelect) {
    elements.archiveTimeSelect.disabled = false;
  }

  if (!state.selectedArchiveDate || !dates.includes(state.selectedArchiveDate)) {
    state.selectedArchiveDate = dates[0];
  }

  for (const date of dates) {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    option.selected = date === state.selectedArchiveDate;
    elements.archiveDateSelect?.appendChild(option);
  }

  const archives = getArchivesForDate(state.selectedArchiveDate);
  if (!archives.some((item) => item.id === state.selectedArchiveId)) {
    state.selectedArchiveId = archives[0]?.id || "";
  }

  for (const archive of archives) {
    const option = document.createElement("option");
    option.value = archive.id;
    option.textContent = archive.time;
    option.selected = archive.id === state.selectedArchiveId;
    elements.archiveTimeSelect?.appendChild(option);
  }
}

function archiveCard(item) {
  return `
    <article class="archive-card">
      <div class="item-meta">
        <span>${escapeHtml(item.source || "Unknown")}</span>
        <span>${escapeHtml(groupLabels[item.group] || item.group || "")}</span>
      </div>
      <h4>${escapeHtml(item.rank ?? "-")}. ${escapeHtml(item.title || "제목 없음")}</h4>
      <p>${escapeHtml(item.importance_reason || item.score_reason || "선정 이유 없음")}</p>
      <a class="source-button secondary" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">원문 보기</a>
    </article>
  `;
}

function renderArchiveBriefing(briefing, archiveMeta) {
  const categoryTop5 = briefing.category_top5 || {};
  const keywords = (briefing.hot_keywords || []).map((item) => item.keyword).filter(Boolean);

  setHtml(
    elements.archiveViewer,
    `
    <div class="archive-summary">
      <div>
        <span class="summary-label">브리핑 시각</span>
        <strong>${escapeHtml(formatDate(briefing.generated_at || archiveMeta?.generated_at))}</strong>
      </div>
      <div>
        <span class="summary-label">수집 항목 수</span>
        <strong>${escapeHtml(briefing.source_total ?? archiveMeta?.source_total ?? "-")}</strong>
      </div>
      <div>
        <span class="summary-label">핵심 키워드</span>
        <strong>${escapeHtml(keywords.slice(0, 5).join(", ") || "-")}</strong>
      </div>
    </div>

    <section class="archive-section">
      <h3>통합 Top 5</h3>
      <div class="archive-card-grid">
        ${(briefing.integrated_top5 || []).map(archiveCard).join("")}
      </div>
    </section>

    <section class="archive-section">
      <h3>카테고리별 Top 5</h3>
      <div class="archive-category-grid">
        ${["news", "tech_blog", "ai_data"]
          .map(
            (group) => `
              <div>
                <h4>${escapeHtml(groupLabels[group] || group)}</h4>
                <div class="archive-mini-list">
                  ${(categoryTop5[group] || [])
                    .map(
                      (item) => `
                        <a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">
                          ${escapeHtml(item.rank ?? "-")}. ${escapeHtml(item.title || "제목 없음")}
                        </a>
                      `,
                    )
                    .join("")}
                </div>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `,
  );
}

async function loadSelectedArchive() {
  const archiveMeta = (state.archiveIndex?.archives ?? []).find((item) => item.id === state.selectedArchiveId);
  if (!archiveMeta) {
    setText(elements.archiveStatus, "선택한 브리핑을 찾을 수 없습니다.");
    clearElement(elements.archiveViewer);
    return;
  }

  setText(elements.archiveStatus, "지난 브리핑을 불러오는 중입니다.");
  try {
    const response = await fetch(`./${archiveMeta.path_json}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`archive HTTP ${response.status}`);
    }
    const briefing = await response.json();
    setText(elements.archiveStatus, "");
    renderArchiveBriefing(briefing, archiveMeta);
  } catch (error) {
    setText(elements.archiveStatus, `지난 브리핑 로드 실패: ${error.message}`);
    clearElement(elements.archiveViewer);
  }
}

function renderArchiveBrowser() {
  renderArchiveControls();
  if (state.selectedArchiveId) {
    loadSelectedArchive();
  }
}

function renderBriefing() {
  if (!state.briefing) {
    elements.briefingSection?.classList.add("is-empty");
    renderIntegratedTop5();
    renderCategoryTop5(elements.newsTop5, []);
    renderCategoryTop5(elements.techTop5, []);
    renderCategoryTop5(elements.aiTop5, []);
    return;
  }

  elements.briefingSection?.classList.remove("is-empty");
  renderIntegratedTop5();
  renderCategoryTop5(elements.newsTop5, state.briefing.category_top5?.news);
  renderCategoryTop5(elements.techTop5, state.briefing.category_top5?.tech_blog);
  renderCategoryTop5(elements.aiTop5, state.briefing.category_top5?.ai_data);
}

function render() {
  renderMeta();
  renderBriefing();
  renderArchiveBrowser();
  renderItems();
}

async function loadData() {
  showStatus("데이터를 불러오는 중입니다.");
  clearElement(elements.itemsList);

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

    try {
      const archiveResponse = await fetch("./archive/index.json", { cache: "no-store" });
      state.archiveIndex = archiveResponse.ok ? await archiveResponse.json() : null;
    } catch {
      state.archiveIndex = null;
    }

    render();
  } catch (error) {
    setText(elements.updatedAt, "-");
    setText(elements.totalItems, "0");
    showStatus(`data.json 로드 실패: ${error.message}`);
  }
}

elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const selectedGroup = button.dataset.group;
    const shouldDeselect = state.activeGroup === selectedGroup;

    state.activeGroup = shouldDeselect ? null : selectedGroup;
    elements.filterButtons.forEach((target) => target.classList.remove("active"));
    if (!shouldDeselect) {
      button.classList.add("active");
    }
    renderItems();
  });
});

elements.refreshButton?.addEventListener("click", loadData);

elements.archiveDateSelect?.addEventListener("change", () => {
  state.selectedArchiveDate = elements.archiveDateSelect.value;
  state.selectedArchiveId = "";
  renderArchiveControls();
  loadSelectedArchive();
});

elements.archiveTimeSelect?.addEventListener("change", () => {
  state.selectedArchiveId = elements.archiveTimeSelect.value;
  loadSelectedArchive();
});

loadData();
