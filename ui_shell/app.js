const DETAIL_TABS = ["개요", "스크립트", "보이스", "자막", "결과물", "로그"];

const STATUS_MACHINE = [
  "NEW",
  "DOWNLOADING",
  "DOWNLOADED",
  "ANALYZING",
  "DRAFT_READY",
  "VOICE_READY",
  "SUBTITLED",
  "DONE",
  "FAILED",
];

const STATUS_LABELS = {
  NEW: "신규",
  DOWNLOADING: "다운로드 중",
  DOWNLOADED: "다운로드 완료",
  ANALYZING: "AI 분석 중",
  DRAFT_READY: "초안 준비",
  VOICE_READY: "보이스 준비",
  SUBTITLED: "자막 완료",
  DONE: "완료",
  FAILED: "실패",
};

const mockJobs = [
  {
    ticket_id: "TICKET-260322-01",
    partner_name: "클린뷰",
    title: "봄 시즌 릴스 런칭",
    status: "DRAFT_READY",
    source_platform: "instagram",
    source_url: "https://www.instagram.com/reel/CLEANVIEW01",
    keyword: "봄 보습 루틴",
    product_info: "클린뷰 하이드라 세럼 / 30ml / 시즌 한정 세트",
    download_status: "DOWNLOADED",
    local_video_path: "/data/videos/ticket-01/source.mp4",
    download_logs: [
      "2026-03-22T09:08:12Z source url validation passed",
      "2026-03-22T09:08:30Z video download success",
    ],
    partners_link_status: "READY",
    partners_link_url: "https://partners.example.com/p/cleanview-hydra",
    partners_link_error: "",
    video_duration: 20.6,
    draft_script: "첫 3초, 건조한 피부를 바로 진정시키는 장면으로 시작하고 사용 직후 결 정돈 포인트를 강조합니다.",
    draft_instagram_caption: "아침 루틴을 가볍게 바꿔줄 봄 한정 세럼 🌸 지금 링크에서 혜택 확인하세요.",
    gemini_prompt_version: "gemini-prompt-v3.2",
    gemini_script_options: [
      "옵션 A: 후킹 강한 퍼포먼스형",
      "옵션 B: 사용감 중심 신뢰형",
      "옵션 C: 혜택 강조 전환형",
    ],
    voice_script_text: "하루 시작 전, 피부 결부터 정돈되는 봄 보습 루틴. 이번 주 한정 혜택으로 더 가볍게 시작하세요.",
    elevenlabs_audio_path: "/data/audio/ticket-01/voice.mp3",
    subtitle_file_path: "/data/subtitles/ticket-01/subtitle.srt",
    final_video_path: "",
    created_at: "2026-03-22T09:05:00Z",
    due_at: "2026-03-22T18:00:00Z",
    owner: "운영 1팀",
    tags: ["신규 캠페인", "핑크 톤"],
    pipeline_logs: [
      { time: "09:10", title: "티켓 생성", detail: "신규 티켓이 생성되었습니다." },
      { time: "10:30", title: "Gemini 초안 생성", detail: "스크립트 3안과 캡션 초안이 생성되었습니다." },
    ],
  },
  {
    ticket_id: "TICKET-260322-02",
    partner_name: "루미엘",
    title: "신제품 티저 숏폼",
    status: "ANALYZING",
    source_platform: "tiktok",
    source_url: "https://www.tiktok.com/@lumiel/video/987654",
    keyword: "런칭 티저",
    product_info: "루미엘 글로우 쿠션 / 런칭 전 티저",
    download_status: "DOWNLOADED",
    local_video_path: "/data/videos/ticket-02/source.mp4",
    download_logs: [
      "2026-03-21T14:01:02Z source fetch queued",
      "2026-03-21T14:01:44Z download complete",
    ],
    partners_link_status: "PENDING",
    partners_link_url: "",
    partners_link_error: "",
    video_duration: 12.2,
    draft_script: "",
    draft_instagram_caption: "",
    gemini_prompt_version: "gemini-prompt-v3.2",
    gemini_script_options: ["", "", ""],
    voice_script_text: "",
    elevenlabs_audio_path: "",
    subtitle_file_path: "",
    final_video_path: "",
    created_at: "2026-03-21T14:00:00Z",
    due_at: "2026-03-23T11:00:00Z",
    owner: "운영 2팀",
    tags: ["티저", "짧은 컷"],
    pipeline_logs: [
      { time: "14:05", title: "티켓 생성", detail: "티저 숏폼 티켓이 등록되었습니다." },
      { time: "15:20", title: "분석 진행", detail: "컷 분할 및 키포인트 분석을 진행 중입니다." },
    ],
  },
  {
    ticket_id: "TICKET-260322-03",
    partner_name: "오브제이",
    title: "주간 성과 리마인드 영상",
    status: "DONE",
    source_platform: "youtube_shorts",
    source_url: "https://youtube.com/shorts/OBJEY7788",
    keyword: "베스트셀러 리마인드",
    product_info: "오브제이 베스트 구성 리마인드",
    download_status: "DOWNLOADED",
    local_video_path: "/data/videos/ticket-03/source.mp4",
    download_logs: [
      "2026-03-19T08:58:01Z download complete",
      "2026-03-19T09:02:10Z checksum verified",
    ],
    partners_link_status: "READY",
    partners_link_url: "https://partners.example.com/p/objey-best",
    partners_link_error: "",
    video_duration: 15.1,
    draft_script: "지난주 가장 반응 좋았던 핵심 컷과 혜택을 빠르게 다시 노출합니다.",
    draft_instagram_caption: "이번 주도 베스트 구성으로 빠르게 결정해보세요. 링크에서 바로 확인 ✅",
    gemini_prompt_version: "gemini-prompt-v3.1",
    gemini_script_options: [
      "옵션 A: 성과 수치 강조",
      "옵션 B: 고객 반응 중심",
      "옵션 C: 혜택/마감 강조",
    ],
    voice_script_text: "지금 가장 많이 선택된 구성을 짧게 확인해보세요. 익숙해서 더 빠르게 결정됩니다.",
    elevenlabs_audio_path: "/data/audio/ticket-03/voice.mp3",
    subtitle_file_path: "/data/subtitles/ticket-03/subtitle.srt",
    final_video_path: "/data/final/ticket-03/final.mp4",
    created_at: "2026-03-19T08:40:00Z",
    due_at: "2026-03-20T12:00:00Z",
    owner: "운영 1팀",
    tags: ["리마인드", "성과형"],
    pipeline_logs: [
      { time: "09:00", title: "최종 렌더", detail: "최종 영상 렌더가 완료되었습니다." },
      { time: "09:18", title: "업로드 완료", detail: "파트너스 링크 포함 업로드를 완료했습니다." },
    ],
  },
];

const initialDraft = () => ({
  partner: "",
  contentType: "릴스 광고",
  channel: "instagram",
  tone: "프리미엄 미니멀",
  dueDate: "2026-03-24",
  memo: "",
});

const state = {
  route: "login",
  authenticated: false,
  activeTab: "개요",
  selectedJobId: mockJobs[0].ticket_id,
  statusFilter: "전체",
  searchQuery: "",
  createDraft: initialDraft(),
};

const root = document.querySelector("#app");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function statusToPercent(status) {
  const index = Math.max(0, STATUS_MACHINE.indexOf(status));
  return Math.round((index / (STATUS_MACHINE.length - 1)) * 100);
}

function displayStatus(status) {
  return STATUS_LABELS[status] || status;
}

function badgeTone(label) {
  if (["FAILED", "실패", "ERROR"].includes(label)) return "badge-rose";
  if (["DONE", "완료", "READY"].includes(label)) return "badge-ink";
  return "badge-soft";
}

function renderBadge(label) {
  return `<span class="badge ${badgeTone(label)}">${escapeHtml(label)}</span>`;
}

function renderTopbar({ title, subtitle, backRoute, rightContent = "" }) {
  const leading = backRoute
    ? `<button class="icon-button" type="button" data-action="navigate" data-route="${backRoute}" aria-label="이전 화면">←</button>`
    : `<div class="avatar">KP</div>`;
  return `<header class="topbar"><div class="topbar-side">${leading}</div><div class="topbar-main"><p class="label">${escapeHtml(subtitle)}</p><h1 class="title-lg">${escapeHtml(title)}</h1></div><div class="topbar-side">${rightContent}</div></header>`;
}

function renderSectionHeader(kicker, title) {
  return `<div class="section-header"><div class="section-copy"><p class="label">${escapeHtml(kicker)}</p><h2 class="title-md">${escapeHtml(title)}</h2></div></div>`;
}

function renderProgress(value) {
  return `<div class="progress-bar" aria-hidden="true"><div class="progress-value" style="width: ${Math.max(0, Math.min(100, value))}%"></div></div>`;
}

function renderInfoCard(label, value) {
  return `<div class="info-card"><p class="label">${escapeHtml(label)}</p><span class="info-value">${escapeHtml(value)}</span></div>`;
}

function formatDateLabel(iso) {
  if (!iso) return "-";
  return iso.slice(0, 16).replace("T", " ");
}

function renderJobCard(job) {
  const progress = statusToPercent(job.status);
  return `
    <button class="card job-card" type="button" data-action="open-job" data-job-id="${job.ticket_id}">
      <div class="job-card-header">
        <div class="job-card-title">
          <div class="badge-row">${renderBadge(displayStatus(job.status))}${renderBadge(job.source_platform)}</div>
          <h3 class="title-md">${escapeHtml(job.title)}</h3>
          <p class="body-md">${escapeHtml(job.partner_name)} · ${escapeHtml(job.ticket_id)}</p>
        </div>
        ${renderBadge(job.download_status)}
      </div>
      <div class="job-card-title">
        <div class="meta-row"><span class="helper-note">마감 ${escapeHtml(formatDateLabel(job.due_at))}</span><span class="helper-note">담당 ${escapeHtml(job.owner)}</span></div>
        ${renderProgress(progress)}
        <div class="meta-row"><p class="body-sm">Gemini ${escapeHtml(job.gemini_prompt_version)}</p><p class="body-sm">링크 ${escapeHtml(job.partners_link_status)}</p></div>
      </div>
    </button>`;
}

function renderBottomNav() {
  const items = [{ label: "대시보드", route: "dashboard" }, { label: "작업 목록", route: "job-list" }, { label: "작업 생성", route: "create-job" }, { label: "상세 보기", route: "job-detail" }];
  return `<div class="bottom-nav-wrap"><nav class="bottom-nav" aria-label="주요 메뉴">${items.map((item) => `<button type="button" class="${state.route === item.route ? "is-active" : ""}" data-action="navigate" data-route="${item.route}">${escapeHtml(item.label)}</button>`).join("")}</nav></div>`;
}

function renderLoginScreen() { return `<main class="screen screen-login"><div class="lockup"><span class="eyebrow">모바일 퍼스트 목업</span><h1 class="title-xl">키킷 파트너스 스튜디오</h1><p class="body-lg">티켓 단위 스키마 기준으로 UI 목업을 점검합니다.</p></div><form id="login-form" class="card card-padding stack"><label class="input-wrap"><span class="label">이메일</span><input class="input" type="email" name="email" value="studio@kikitpartners.co"></label><label class="input-wrap"><span class="label">비밀번호</span><input class="input" type="password" name="password" value="••••••••"></label><button class="button button-primary" type="submit">시작하기</button></form></main>`; }

function renderDashboardScreen() {
  const activeJobs = mockJobs.filter((job) => ["DOWNLOADING", "DOWNLOADED", "ANALYZING", "DRAFT_READY", "VOICE_READY", "SUBTITLED"].includes(job.status)).length;
  const doneJobs = mockJobs.filter((job) => job.status === "DONE").length;
  const failedJobs = mockJobs.filter((job) => job.status === "FAILED").length;
  const newJobs = mockJobs.filter((job) => job.status === "NEW").length;
  return `<main class="screen">${renderTopbar({ title: "대시보드", subtitle: "티켓 상태 머신", rightContent: '<span class="helper-note">mock fixture</span>' })}<section class="section">${renderSectionHeader("오늘 요약", "핵심 지표")}<div class="stat-grid"><div class="stat-card"><span class="metric-value">${newJobs}건</span><p class="body-sm">NEW</p></div><div class="stat-card"><span class="metric-value">${activeJobs}건</span><p class="body-sm">진행 중</p></div><div class="stat-card"><span class="metric-value">${doneJobs}건</span><p class="body-sm">DONE</p></div><div class="stat-card"><span class="metric-value">${failedJobs}건</span><p class="body-sm">FAILED</p></div></div></section><section class="section">${renderSectionHeader("최근 티켓", "우선 확인")}<div class="job-list">${mockJobs.slice(0, 2).map(renderJobCard).join("")}</div></section></main>`;
}

function renderCreateScreen() {
  return `<main class="screen">${renderTopbar({ title: "작업 생성", subtitle: "티켓 생성", backRoute: "dashboard", rightContent: renderBadge("NEW") })}<form id="job-create-form" class="section"><div class="card card-padding form-grid"><label class="input-wrap"><span class="label">파트너명</span><input class="input" type="text" name="partner" value="${escapeHtml(state.createDraft.partner)}"></label><label class="input-wrap"><span class="label">콘텐츠 유형</span><input class="input" type="text" name="contentType" value="${escapeHtml(state.createDraft.contentType)}"></label><label class="input-wrap"><span class="label">소스 플랫폼</span><select class="select" name="channel">${["instagram", "tiktok", "youtube_shorts"].map((option) => `<option value="${option}" ${state.createDraft.channel === option ? "selected" : ""}>${option}</option>`).join("")}</select></label><label class="input-wrap"><span class="label">톤</span><input class="input" type="text" name="tone" value="${escapeHtml(state.createDraft.tone)}"></label><label class="input-wrap"><span class="label">마감일</span><input class="input" type="date" name="dueDate" value="${escapeHtml(state.createDraft.dueDate)}"></label><label class="input-wrap"><span class="label">메모</span><textarea class="textarea" name="memo">${escapeHtml(state.createDraft.memo)}</textarea></label></div><div class="card detail-card sticky-bar"><button class="button button-primary" type="submit">작업 생성하기</button></div></form></main>`;
}

function getFilteredJobs() {
  return mockJobs.filter((job) => {
    const matchesFilter = state.statusFilter === "전체" || job.status === state.statusFilter;
    const haystack = `${job.title} ${job.partner_name} ${job.source_platform} ${job.keyword}`.toLowerCase();
    const matchesSearch = !state.searchQuery || haystack.includes(state.searchQuery.trim().toLowerCase());
    return matchesFilter && matchesSearch;
  });
}

function renderJobListScreen() {
  const filters = ["전체", ...STATUS_MACHINE];
  const filteredJobs = getFilteredJobs();
  return `<main class="screen">${renderTopbar({ title: "작업 목록", subtitle: `전체 ${mockJobs.length}건`, backRoute: "dashboard", rightContent: '<span class="helper-note">상태 머신 필터</span>' })}<section class="stack"><div class="search-wrap"><input class="search-input" type="search" data-role="job-search" placeholder="티켓명, 파트너, 키워드 검색" value="${escapeHtml(state.searchQuery)}"></div><div class="pill-row" aria-label="상태 필터">${filters.map((filter) => `<button class="pill ${state.statusFilter === filter ? "is-active" : ""}" type="button" data-action="set-filter" data-filter="${filter}">${escapeHtml(filter === "전체" ? filter : displayStatus(filter))}</button>`).join("")}</div></section><section class="section"><div class="job-list">${filteredJobs.length ? filteredJobs.map(renderJobCard).join("") : `<div class="card card-padding stack"><h3 class="title-md">조건에 맞는 작업이 없습니다.</h3></div>`}</div></section></main>`;
}

function getSelectedJob() { return mockJobs.find((job) => job.ticket_id === state.selectedJobId) || mockJobs[0]; }

function renderOverviewTab(job) {
  return `<div class="stack"><div class="card detail-card"><div class="badge-row">${renderBadge(displayStatus(job.status))}${renderBadge(job.download_status)}${renderBadge(job.partners_link_status)}</div><div class="info-grid">${renderInfoCard("티켓 ID", job.ticket_id)}${renderInfoCard("소스 플랫폼", job.source_platform)}${renderInfoCard("소스 URL", job.source_url)}${renderInfoCard("키워드", job.keyword)}${renderInfoCard("상품 정보", job.product_info)}${renderInfoCard("로컬 영상", job.local_video_path || "-")}${renderInfoCard("영상 길이", `${job.video_duration || 0}초`)}${renderInfoCard("Gemini 프롬프트", job.gemini_prompt_version)}</div></div></div>`;
}

function renderScriptTab(job) {
  return `<div class="stack"><div class="card script-block"><div class="badge-row">${renderBadge(displayStatus(job.status))}${renderBadge("Gemini")}</div><h3 class="title-md">AI 분석 초안</h3><div class="quote"><p class="body-md">${escapeHtml(job.draft_script || "아직 생성되지 않았습니다.")}</p></div><p class="body-md">캡션: ${escapeHtml(job.draft_instagram_caption || "-")}</p></div><div class="card detail-card"><h3 class="title-md">Gemini 스크립트 옵션(3)</h3><ul class="bullet-list">${job.gemini_script_options.map((option, index) => `<li>${escapeHtml(option || `옵션 ${index + 1} 대기`)}</li>`).join("")}</ul></div></div>`;
}

function renderVoiceTab(job) {
  return `<div class="card detail-card"><div class="info-grid">${renderInfoCard("보이스 스크립트", job.voice_script_text || "-")}${renderInfoCard("ElevenLabs 오디오", job.elevenlabs_audio_path || "-")}${renderInfoCard("파트너스 링크", job.partners_link_url || "-")}${renderInfoCard("링크 오류", job.partners_link_error || "-")}</div></div>`;
}

function renderSubtitleTab(job) {
  return `<div class="card detail-card"><div class="badge-row">${renderBadge(displayStatus(job.status))}${renderBadge("자막")}</div><div class="info-grid">${renderInfoCard("자막 파일", job.subtitle_file_path || "-")}${renderInfoCard("최종 영상", job.final_video_path || "-")}</div></div>`;
}

function renderDeliverablesTab(job) {
  return `<div class="result-grid"><div class="card result-card"><div class="badge-row">${renderBadge(job.download_status)}</div><h3 class="title-md">다운로드</h3><p class="body-md">${escapeHtml(job.local_video_path || "-")}</p></div><div class="card result-card"><div class="badge-row">${renderBadge(job.partners_link_status)}</div><h3 class="title-md">파트너스 링크</h3><p class="body-md">${escapeHtml(job.partners_link_url || job.partners_link_error || "-")}</p></div><div class="card result-card"><div class="badge-row">${renderBadge(displayStatus(job.status))}</div><h3 class="title-md">최종 결과물</h3><p class="body-md">${escapeHtml(job.final_video_path || "아직 생성 전")}</p></div></div>`;
}

function renderLogTab(job) {
  const mergedLogs = [
    ...job.pipeline_logs.map((log) => ({ time: log.time, title: log.title, detail: log.detail })),
    ...job.download_logs.map((line, index) => ({ time: `DL-${index + 1}`, title: "download_logs", detail: line })),
  ];
  return `<div class="card detail-card"><div class="timeline">${mergedLogs.map((log) => `<div class="timeline-item"><div class="badge-row">${renderBadge(log.time)}</div><h3 class="title-md">${escapeHtml(log.title)}</h3><p class="body-md">${escapeHtml(log.detail)}</p></div>`).join("")}</div></div>`;
}

function renderDetailTab(job) {
  const renderers = { 개요: renderOverviewTab, 스크립트: renderScriptTab, 보이스: renderVoiceTab, 자막: renderSubtitleTab, 결과물: renderDeliverablesTab, 로그: renderLogTab };
  return renderers[state.activeTab](job);
}

function renderJobDetailScreen() {
  const job = getSelectedJob();
  const progress = statusToPercent(job.status);
  return `<main class="screen">${renderTopbar({ title: "작업 상세", subtitle: job.ticket_id, backRoute: "job-list", rightContent: renderBadge(displayStatus(job.status)) })}<section class="hero-card card card-padding stack"><div class="badge-row">${job.tags.map(renderBadge).join("")}</div><h2 class="title-lg">${escapeHtml(job.title)}</h2><p class="body-md">${escapeHtml(job.partner_name)} · ${escapeHtml(job.source_platform)} · 마감 ${escapeHtml(formatDateLabel(job.due_at))}</p>${renderProgress(progress)}<div class="meta-row"><span class="helper-note">진행률 ${progress}%</span><span class="helper-note">${escapeHtml(job.download_status)}</span><span class="helper-note">${escapeHtml(job.partners_link_status)}</span></div></section><section class="section"><div class="tab-row" aria-label="상세 탭">${DETAIL_TABS.map((tab) => `<button class="pill ${state.activeTab === tab ? "is-active" : ""}" type="button" data-action="set-tab" data-tab="${tab}">${escapeHtml(tab)}</button>`).join("")}</div>${renderDetailTab(job)}</section></main>`;
}

function renderScreen() {
  if (!state.authenticated && state.route !== "login") state.route = "login";
  if (state.route === "dashboard") return renderDashboardScreen();
  if (state.route === "create-job") return renderCreateScreen();
  if (state.route === "job-list") return renderJobListScreen();
  if (state.route === "job-detail") return renderJobDetailScreen();
  return renderLoginScreen();
}

function render() {
  root.innerHTML = `<div class="app-stage"><div class="phone-shell">${renderScreen()}${state.authenticated ? renderBottomNav() : ""}</div></div>`;
}

function navigate(route) {
  if (route === "login") state.authenticated = false;
  else if (!state.authenticated) state.authenticated = true;
  if (route !== "job-detail") state.activeTab = "개요";
  state.route = route;
  render();
}

function createMockJob(form) {
  const partner = form.get("partner")?.toString().trim() || "새 파트너";
  const contentType = form.get("contentType")?.toString().trim() || "릴스 광고";
  const sourcePlatform = form.get("channel")?.toString().trim() || "instagram";
  const tone = form.get("tone")?.toString().trim() || "프리미엄 미니멀";
  const dueDate = form.get("dueDate")?.toString().trim() || "2026-03-24";
  const memo = form.get("memo")?.toString().trim() || "요청 메모 없음";
  const lastIndex = String(mockJobs.length + 1).padStart(2, "0");

  const newJob = {
    ticket_id: `TICKET-260322-${lastIndex}`,
    partner_name: partner,
    title: `${partner} ${contentType}`,
    status: "NEW",
    source_platform: sourcePlatform,
    source_url: "",
    keyword: contentType,
    product_info: memo,
    download_status: "NEW",
    local_video_path: "",
    download_logs: ["ticket created"],
    partners_link_status: "PENDING",
    partners_link_url: "",
    partners_link_error: "",
    video_duration: 0,
    draft_script: "",
    draft_instagram_caption: "",
    gemini_prompt_version: "gemini-prompt-v3.2",
    gemini_script_options: ["", "", ""],
    voice_script_text: tone,
    elevenlabs_audio_path: "",
    subtitle_file_path: "",
    final_video_path: "",
    created_at: "2026-03-22T00:00:00Z",
    due_at: `${dueDate}T18:00:00Z`,
    owner: "운영 신작업",
    tags: ["신규 생성", tone],
    pipeline_logs: [
      { time: "지금", title: "티켓 생성", detail: `${partner} ${contentType} 티켓이 생성되었습니다.` },
    ],
  };

  mockJobs.unshift(newJob);
  state.selectedJobId = newJob.ticket_id;
  state.route = "job-detail";
  state.activeTab = "개요";
  state.searchQuery = "";
  state.statusFilter = "전체";
  state.createDraft = initialDraft();
  render();
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const { action } = target.dataset;
  if (action === "navigate") return navigate(target.dataset.route);
  if (action === "open-job") {
    state.selectedJobId = target.dataset.jobId;
    state.route = "job-detail";
    state.activeTab = "개요";
    state.authenticated = true;
    return render();
  }
  if (action === "set-tab") {
    state.activeTab = target.dataset.tab;
    return render();
  }
  if (action === "set-filter") {
    state.statusFilter = target.dataset.filter;
    return render();
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement)) return;
  if (target.dataset.role === "job-search") {
    state.searchQuery = target.value;
    return render();
  }
  if (target.form?.id === "job-create-form" && target.name in state.createDraft) state.createDraft[target.name] = target.value;
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  if (form.id === "login-form") {
    state.authenticated = true;
    state.route = "dashboard";
    return render();
  }
  if (form.id === "job-create-form") createMockJob(new FormData(form));
});

render();
