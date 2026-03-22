const DETAIL_TABS = ["개요", "스크립트", "보이스", "자막", "결과물", "로그"];

const WIZARD_STEPS = [
  { route: "ticket-link", label: "링크입력" },
  { route: "ticket-download", label: "다운로드진행" },
  { route: "ticket-keyword", label: "키워드입력" },
  { route: "ticket-partners-link", label: "파트너스링크생성" },
  { route: "ticket-analysis", label: "AI분석초안" },
  { route: "ticket-script", label: "스크립트생성" },
  { route: "ticket-voice", label: "보이스생성" },
  { route: "ticket-subtitle", label: "자막합성" },
  { route: "ticket-result", label: "최종결과" },
];

const initialJobs = [
  {
    id: "JOB-260322-01",
    partner: "클린뷰",
    title: "봄 시즌 릴스 런칭",
    status: "진행 중",
    progress: 72,
    dueLabel: "오늘 18:00",
    channel: "인스타 릴스",
    createdAt: "2026.03.22",
    owner: "운영 1팀",
    priority: "높음",
    tags: ["신규 캠페인", "핑크 톤"],
    overview: {
      summary: "봄 프로모션용 20초 세로형 영상 3편을 제작하는 작업입니다.",
      goal: "초반 3초 후킹과 전환 유도를 함께 잡는 퍼포먼스형 숏폼.",
      notes: [
        "첫 컷은 제품보다 사용 장면을 우선 배치",
        "혜택 문구는 자막으로 반복 노출",
        "브랜드 톤은 차분하지만 답답하지 않게 유지",
      ],
    },
    script: {
      headline: "첫 3초 안에 바로 사고 싶게 만드는 봄 케어 루틴",
      body: [
        "아침에 바르자마자 피부 결이 정돈되는 느낌.",
        "메이크업 전에 발라도 밀리지 않아서 준비가 훨씬 가벼워집니다.",
        "이번 시즌 한정 혜택으로 지금이 가장 좋은 타이밍이라는 점을 강조합니다.",
      ],
      cta: "지금 링크에서 한정 구성 확인하기",
      status: "검수 대기",
    },
    voice: {
      talent: "소연",
      mood: "따뜻하고 신뢰감 있는 톤",
      speed: "0.96x",
      pitch: "+1",
      memo: "브랜드명은 천천히, 혜택 문구는 리듬감 있게 읽기",
      status: "녹음 예약",
    },
    subtitles: {
      style: "오프화이트 박스 + 소프트 핑크 포인트",
      emphasis: "핵심 키워드만 굵게 처리",
      sample: [
        "하루 시작 전, 피부 결부터 달라지는 루틴",
        "메이크업 전에 발라도 가볍고 편안하게",
        "이번 주 한정 혜택까지 바로 확인",
      ],
      status: "1차 완료",
    },
    deliverables: [
      { label: "세로형 MP4", note: "1080x1920 / 30fps", status: "렌더링 대기" },
      { label: "썸네일", note: "정사각형 1종", status: "시안 완료" },
      { label: "업로드 캡션", note: "CTA 포함 2안", status: "작성 중" },
    ],
    logs: [
      { time: "09:10", title: "작업 생성", detail: "클린뷰 봄 시즌 릴스 런칭 작업이 시작되었습니다." },
      { time: "10:25", title: "스크립트 1차 작성", detail: "후킹 중심 스크립트 초안이 생성되었습니다." },
      { time: "11:40", title: "자막 시안 반영", detail: "짧은 행 길이 기준으로 자막 톤이 정리되었습니다." },
    ],
  },
  {
    id: "JOB-260322-02",
    partner: "루미엘",
    title: "신제품 티저 숏폼",
    status: "검수 대기",
    progress: 54,
    dueLabel: "내일 11:00",
    channel: "틱톡",
    createdAt: "2026.03.21",
    owner: "운영 2팀",
    priority: "중간",
    tags: ["티저", "짧은 컷"],
    overview: {
      summary: "런칭 전 기대감을 높이는 12초 티저 영상 셸입니다.",
      goal: "제품 공개 전 감각적인 무드 컷과 짧은 카피로 저장 유도.",
      notes: [
        "정면 제품 컷은 마지막 2초에서만 노출",
        "자막은 최대 두 줄을 넘기지 않기",
        "보이스 없이 효과음 중심으로 구성 가능",
      ],
    },
    script: {
      headline: "보기만 해도 저장하고 싶은 런칭 직전 티저",
      body: [
        "빛이 닿는 순간부터 분위기가 달라집니다.",
        "곧 공개될 새로운 컬렉션, 먼저 감각만 남겨보세요.",
      ],
      cta: "알림 설정하고 런칭 소식 가장 먼저 받기",
      status: "검수 대기",
    },
    voice: {
      talent: "민지",
      mood: "담백하고 세련된 톤",
      speed: "1.02x",
      pitch: "0",
      memo: "보이스는 선택 옵션, 무음 버전도 함께 준비",
      status: "옵션 검토",
    },
    subtitles: {
      style: "얇은 세리프 포인트 + 여백 많은 배치",
      emphasis: "핵심 명사만 포인트 컬러",
      sample: [
        "곧 공개될 새로운 무드",
        "런칭 전 가장 먼저 만나보세요",
      ],
      status: "초안",
    },
    deliverables: [
      { label: "티저 MP4", note: "1080x1920 / 12초", status: "편집 중" },
      { label: "무음 버전", note: "보이스 제외", status: "기획 완료" },
    ],
    logs: [
      { time: "14:05", title: "시안 요청 접수", detail: "티저 무드 레퍼런스 3종이 정리되었습니다." },
      { time: "15:20", title: "스크립트 검수 대기", detail: "카피 길이를 줄인 버전으로 업데이트되었습니다." },
    ],
  },
  {
    id: "JOB-260322-03",
    partner: "오브제이",
    title: "주간 성과 리마인드 영상",
    status: "완료",
    progress: 100,
    dueLabel: "완료됨",
    channel: "유튜브 쇼츠",
    createdAt: "2026.03.19",
    owner: "운영 1팀",
    priority: "낮음",
    tags: ["리마인드", "성과형"],
    overview: {
      summary: "지난 주 베스트 성과 상품 리마인드 영상입니다.",
      goal: "재방문 고객에게 익숙한 혜택 메시지를 다시 노출.",
      notes: [
        "베스트 컷 중심으로 빠르게 리듬감 유지",
        "문장 길이는 짧고 바로 이해되게 구성",
      ],
    },
    script: {
      headline: "지난주 가장 많이 선택된 이유를 다시 보여주는 영상",
      body: [
        "지금 가장 반응 좋은 구성을 짧게 다시 확인해보세요.",
        "이미 검증된 선택이라 더 빠르게 결정할 수 있습니다.",
      ],
      cta: "오늘 안에 베스트 구성 확인하기",
      status: "승인 완료",
    },
    voice: {
      talent: "도윤",
      mood: "빠르고 또렷한 톤",
      speed: "1.04x",
      pitch: "-1",
      memo: "성과 수치는 또렷하게 끊어 읽기",
      status: "완료",
    },
    subtitles: {
      style: "심플 화이트 + 연핑크 언더라인",
      emphasis: "숫자와 혜택 문구 우선",
      sample: [
        "지금 가장 많이 선택된 구성",
        "익숙해서 더 빠르게 결정되는 이유",
      ],
      status: "완료",
    },
    deliverables: [
      { label: "최종 MP4", note: "업로드 완료", status: "완료" },
      { label: "썸네일", note: "A/B 2안", status: "완료" },
      { label: "업로드 로그", note: "전송 성공", status: "완료" },
    ],
    logs: [
      { time: "09:00", title: "최종 렌더 완료", detail: "업로드용 파일 렌더가 정상 완료되었습니다." },
      { time: "09:18", title: "업로드 전송 완료", detail: "플랫폼 업로드와 확인 로그가 정리되었습니다." },
    ],
  },
];

const SUPPORTED_PLATFORMS = [
  { key: "youtube", label: "유튜브", hosts: ["youtube.com", "youtu.be"] },
  { key: "instagram", label: "인스타그램", hosts: ["instagram.com"] },
  { key: "tiktok", label: "틱톡", hosts: ["tiktok.com"] },
];

const initialTicketDraft = () => ({
  sourceLink: "",
  platform: "",
  downloadProgress: 0,
  keywords: "",
  partnersLink: "",
  analysisDraft: "",
  scriptDraft: "",
  voiceStatus: "",
  subtitleStatus: "",
  resultSummary: "",
  completedAt: "",
});

const state = {
  route: "login",
  authenticated: false,
  activeTab: "개요",
  selectedJobId: initialJobs[0].id,
  statusFilter: "전체",
  searchQuery: "",
  jobs: [...initialJobs],
  ticketDraft: initialTicketDraft(),
  wizardError: "",
};

const root = document.querySelector("#app");

function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }

function badgeTone(label) {
  if (["진행 중", "높음", "검수 대기", "렌더링 대기", "녹음 예약", "작성 중", "생성 중"].includes(label)) return "badge-rose";
  if (["완료", "완료됨", "승인 완료", "생성 완료"].includes(label)) return "badge-ink";
  return "badge-soft";
}

const renderBadge = (label) => `<span class="badge ${badgeTone(label)}">${escapeHtml(label)}</span>`;

function renderTopbar({ title, subtitle, backRoute, rightContent = "" }) {
  const leading = backRoute
    ? `<button class="icon-button" type="button" data-action="navigate" data-route="${backRoute}" aria-label="이전 화면">←</button>`
    : '<div class="avatar">KP</div>';
  return `<header class="topbar"><div class="topbar-side">${leading}</div><div class="topbar-main"><p class="label">${escapeHtml(subtitle)}</p><h1 class="title-lg">${escapeHtml(title)}</h1></div><div class="topbar-side">${rightContent}</div></header>`;
}

function renderSectionHeader(kicker, title, actionLabel = "", actionRoute = "") {
  const action = actionLabel && actionRoute ? `<button class="ghost-button" type="button" data-action="navigate" data-route="${actionRoute}">${escapeHtml(actionLabel)}</button>` : "";
  return `<div class="section-header"><div class="section-copy"><p class="label">${escapeHtml(kicker)}</p><h2 class="title-md">${escapeHtml(title)}</h2></div>${action}</div>`;
}

const renderProgress = (value) => `<div class="progress-bar" aria-hidden="true"><div class="progress-value" style="width: ${Math.max(0, Math.min(100, value))}%"></div></div>`;
const renderInfoCard = (label, value) => `<div class="info-card"><p class="label">${escapeHtml(label)}</p><span class="info-value">${escapeHtml(value)}</span></div>`;

function renderMenuTile(title, note, route) {
  return `<button class="menu-tile card-inset" type="button" data-action="navigate" data-route="${route}"><span class="menu-kicker">${escapeHtml(title)}</span><p class="body-sm">${escapeHtml(note)}</p></button>`;
}

function renderWizardProgress() {
  const currentIndex = WIZARD_STEPS.findIndex((step) => step.route === state.route);
  return `<div class="card card-padding stack"><p class="label">생성 위저드</p><div class="pill-row">${WIZARD_STEPS.map((step, index) => `<span class="pill ${index <= currentIndex ? "is-active" : ""}">${index + 1}. ${escapeHtml(step.label)}</span>`).join("")}</div>${state.wizardError ? `<p class="body-sm" style="color:#b42318;">${escapeHtml(state.wizardError)}</p>` : ""}</div>`;
}

function renderJobCard(job) {
  return `<button class="card job-card" type="button" data-action="open-job" data-job-id="${job.id}"><div class="job-card-header"><div class="job-card-title"><div class="badge-row">${renderBadge(job.status)}${renderBadge(job.channel)}</div><h3 class="title-md">${escapeHtml(job.title)}</h3><p class="body-md">${escapeHtml(job.partner)} · ${escapeHtml(job.id)}</p></div>${renderBadge(job.priority)}</div><div class="job-card-title"><div class="meta-row"><span class="helper-note">마감 ${escapeHtml(job.dueLabel)}</span><span class="helper-note">담당 ${escapeHtml(job.owner)}</span></div>${renderProgress(job.progress)}<div class="meta-row"><p class="body-sm">스크립트 ${escapeHtml(job.script.status)}</p><p class="body-sm">자막 ${escapeHtml(job.subtitles.status)}</p></div></div></button>`;
}

function renderBottomNav() {
  const items = [
    { label: "대시보드", route: "dashboard" },
    { label: "작업 목록", route: "job-list" },
    { label: "티켓 생성", route: "ticket-link" },
    { label: "상세 보기", route: "job-detail" },
  ];
  return `<div class="bottom-nav-wrap"><nav class="bottom-nav" aria-label="주요 메뉴">${items.map((item) => `<button type="button" class="${state.route === item.route ? "is-active" : ""}" data-action="navigate" data-route="${item.route}">${escapeHtml(item.label)}</button>`).join("")}</nav></div>`;
}

function renderLoginScreen() { return `<main class="screen screen-login"><div class="lockup"><span class="eyebrow">모바일 퍼스트 목업</span><h1 class="title-xl">키킷 파트너스 스튜디오</h1><p class="body-lg">실제 티켓 생성 위저드 구조를 반영한 작업 셸입니다.</p></div><form id="login-form" class="card card-padding stack"><label class="input-wrap"><span class="label">이메일</span><input class="input" type="email" name="email" value="studio@kikitpartners.co"></label><label class="input-wrap"><span class="label">비밀번호</span><input class="input" type="password" name="password" value="••••••••"></label><button class="button button-primary" type="submit">시작하기</button></form><div class="card card-padding stack"><p class="label">바로 확인할 메뉴</p><div class="menu-grid">${renderMenuTile("대시보드", "진행 현황 요약", "dashboard")}${renderMenuTile("티켓 생성", "단계형 생성 위저드", "ticket-link")}${renderMenuTile("작업 목록", "전체 티켓 상태 확인", "job-list")}${renderMenuTile("상세 보기", "완료 티켓 탭 확인", "job-detail")}</div></div></main>`; }

function renderDashboardScreen() {
  const jobs = state.jobs;
  const activeJobs = jobs.filter((job) => job.status === "진행 중").length;
  const reviewJobs = jobs.filter((job) => job.script.status === "검수 대기").length;
  const doneJobs = jobs.filter((job) => job.status === "완료").length;
  const todayJobs = jobs.filter((job) => job.dueLabel.includes("오늘")).length;
  return `<main class="screen">${renderTopbar({ title: "대시보드", subtitle: "오늘의 작업 흐름", rightContent: '<span class="helper-note">실제 워크플로우</span>' })}<section class="hero-card card card-padding stack"><h2 class="title-lg">티켓 생성은 단계형 위저드에서 진행하고 완료 후 상세 탭에서 확인합니다.</h2><div class="button-row"><button class="button button-primary" type="button" data-action="navigate" data-route="ticket-link">새 티켓 만들기</button><button class="button button-secondary" type="button" data-action="navigate" data-route="job-list">작업 목록 보기</button></div></section><section class="section">${renderSectionHeader("오늘 요약", "핵심 지표")}<div class="stat-grid"><div class="stat-card"><span class="metric-value">${activeJobs}건</span><p class="body-sm">진행 중 작업</p></div><div class="stat-card"><span class="metric-value">${todayJobs}건</span><p class="body-sm">오늘 마감</p></div><div class="stat-card"><span class="metric-value">${reviewJobs}건</span><p class="body-sm">검수 대기</p></div><div class="stat-card"><span class="metric-value">${doneJobs}건</span><p class="body-sm">완료 작업</p></div></div></section></main>`;
}

function getFilteredJobs() {
  return state.jobs.filter((job) => {
    const matchesFilter = state.statusFilter === "전체" || job.status === state.statusFilter || job.script.status === state.statusFilter;
    const haystack = `${job.title} ${job.partner} ${job.channel}`.toLowerCase();
    const matchesSearch = !state.searchQuery || haystack.includes(state.searchQuery.trim().toLowerCase());
    return matchesFilter && matchesSearch;
  });
}

function renderJobListScreen() {
  const filters = ["전체", "진행 중", "검수 대기", "완료"];
  const filteredJobs = getFilteredJobs();
  return `<main class="screen">${renderTopbar({ title: "작업 목록", subtitle: `전체 ${state.jobs.length}건`, backRoute: "dashboard", rightContent: '<span class="helper-note">필터 가능</span>' })}<section class="stack"><div class="search-wrap"><input class="search-input" type="search" data-role="job-search" placeholder="작업명, 파트너명, 채널 검색" value="${escapeHtml(state.searchQuery)}"></div><div class="pill-row" aria-label="상태 필터">${filters.map((filter) => `<button class="pill ${state.statusFilter === filter ? "is-active" : ""}" type="button" data-action="set-filter" data-filter="${filter}">${escapeHtml(filter)}</button>`).join("")}</div></section><section class="section">${renderSectionHeader("작업 카드", "모바일 스캔 리스트", "새 티켓", "ticket-link")}<div class="job-list">${filteredJobs.length ? filteredJobs.map(renderJobCard).join("") : `<div class="card card-padding stack"><h3 class="title-md">조건에 맞는 작업이 없습니다.</h3><p class="body-md">검색어나 상태 필터를 조정해 보세요.</p></div>`}</div></section></main>`;
}

function detectPlatform(link) {
  try {
    const host = new URL(link).hostname.replace("www.", "");
    return SUPPORTED_PLATFORMS.find((platform) => platform.hosts.some((supportedHost) => host.includes(supportedHost))) || null;
  } catch {
    return null;
  }
}

function renderLinkStep() {
  return `<section class="section stack">${renderWizardProgress()}<form id="ticket-link-form" class="card card-padding stack"><h2 class="title-lg">1) 링크 입력</h2><label class="input-wrap"><span class="label">원본 콘텐츠 링크</span><input class="input" type="url" name="sourceLink" placeholder="https://..." value="${escapeHtml(state.ticketDraft.sourceLink)}"></label><p class="helper-note">지원 플랫폼: 유튜브 / 인스타그램 / 틱톡</p><button class="button button-primary" type="submit">다운로드 단계로 이동</button></form></section>`;
}
function renderDownloadStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">2) 다운로드 진행</h2><p class="body-md">플랫폼: ${renderBadge(state.ticketDraft.platform || "미확인")}</p>${renderProgress(state.ticketDraft.downloadProgress)}<p class="body-sm">현재 진행률 ${state.ticketDraft.downloadProgress}%</p><div class="button-row"><button class="button button-secondary" type="button" data-action="download-progress">진행률 +25%</button><button class="button button-primary" type="button" data-action="goto-step" data-route="ticket-keyword">키워드 입력 단계</button></div></div></section>`;
}
function renderKeywordStep() {
  return `<section class="section stack">${renderWizardProgress()}<form id="ticket-keyword-form" class="card card-padding stack"><h2 class="title-lg">3) 키워드 입력</h2><label class="input-wrap"><span class="label">핵심 키워드</span><input class="input" type="text" name="keywords" placeholder="예: 봄케어, 보습, 한정혜택" value="${escapeHtml(state.ticketDraft.keywords)}"></label><button class="button button-primary" type="submit">파트너스 링크 생성</button></form></section>`;
}
function renderPartnersLinkStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">4) 파트너스 링크 생성</h2><p class="body-md">생성 링크: ${escapeHtml(state.ticketDraft.partnersLink || "아직 생성 전")}</p><button class="button button-primary" type="button" data-action="generate-partners-link">AI 분석 초안으로 이동</button></div></section>`;
}
function renderAnalysisStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">5) AI 분석 초안</h2><p class="body-md">${escapeHtml(state.ticketDraft.analysisDraft || "분석 초안을 생성해 주세요.")}</p><button class="button button-primary" type="button" data-action="generate-analysis">스크립트 생성으로 이동</button></div></section>`;
}
function renderScriptStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">6) 스크립트 생성</h2><div class="quote"><p class="body-md">${escapeHtml(state.ticketDraft.scriptDraft || "스크립트를 생성해 주세요.")}</p></div><button class="button button-primary" type="button" data-action="generate-script">보이스 생성으로 이동</button></div></section>`;
}
function renderVoiceStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">7) 보이스 생성</h2><p class="body-md">상태: ${escapeHtml(state.ticketDraft.voiceStatus || "대기")}</p><button class="button button-primary" type="button" data-action="generate-voice">자막 합성으로 이동</button></div></section>`;
}
function renderSubtitleStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">8) 자막 합성</h2><p class="body-md">상태: ${escapeHtml(state.ticketDraft.subtitleStatus || "대기")}</p><button class="button button-primary" type="button" data-action="generate-subtitle">최종 결과로 이동</button></div></section>`;
}
function renderResultStep() {
  return `<section class="section stack">${renderWizardProgress()}<div class="card card-padding stack"><h2 class="title-lg">9) 최종 결과</h2><p class="body-md">${escapeHtml(state.ticketDraft.resultSummary || "결과 요약 생성 전")}</p><button class="button button-primary" type="button" data-action="complete-ticket">완료 티켓 생성</button></div></section>`;
}

function renderWizardScreen() {
  const titles = Object.fromEntries(WIZARD_STEPS.map((s) => [s.route, s.label]));
  const stepRenderers = {
    "ticket-link": renderLinkStep,
    "ticket-download": renderDownloadStep,
    "ticket-keyword": renderKeywordStep,
    "ticket-partners-link": renderPartnersLinkStep,
    "ticket-analysis": renderAnalysisStep,
    "ticket-script": renderScriptStep,
    "ticket-voice": renderVoiceStep,
    "ticket-subtitle": renderSubtitleStep,
    "ticket-result": renderResultStep,
  };
  return `<main class="screen">${renderTopbar({ title: "티켓 생성", subtitle: titles[state.route], backRoute: "dashboard", rightContent: renderBadge("위저드") })}${stepRenderers[state.route]()}</main>`;
}

function getSelectedJob() { return state.jobs.find((job) => job.id === state.selectedJobId) || state.jobs[0]; }
function renderOverviewTab(job) { return `<div class="stack"><div class="card detail-card"><div class="badge-row">${renderBadge(job.status)}${renderBadge(job.channel)}${renderBadge(job.script.status)}</div><p class="body-md">${escapeHtml(job.overview.summary)}</p><div class="info-grid">${renderInfoCard("파트너", job.partner)}${renderInfoCard("담당 팀", job.owner)}${renderInfoCard("마감", job.dueLabel)}${renderInfoCard("생성일", job.createdAt)}</div></div><div class="card detail-card"><h3 class="title-md">핵심 목표</h3><p class="body-md">${escapeHtml(job.overview.goal)}</p><ul class="bullet-list">${job.overview.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul></div></div>`; }
function renderScriptTab(job) { return `<div class="stack"><div class="card script-block"><div class="badge-row">${renderBadge(job.script.status)}${renderBadge("스크립트")}</div><h3 class="title-md">${escapeHtml(job.script.headline)}</h3><div class="quote">${job.script.body.map((line) => `<p class="body-md">${escapeHtml(line)}</p>`).join("")}</div></div><div class="card detail-card"><h3 class="title-md">콜 투 액션</h3><p class="body-md">${escapeHtml(job.script.cta)}</p></div></div>`; }
function renderVoiceTab(job) { return `<div class="card detail-card"><div class="badge-row">${renderBadge(job.voice.status)}${renderBadge(job.voice.talent)}</div><div class="info-grid">${renderInfoCard("톤", job.voice.mood)}${renderInfoCard("속도", job.voice.speed)}${renderInfoCard("피치", job.voice.pitch)}${renderInfoCard("메모", job.voice.memo)}</div></div>`; }
function renderSubtitleTab(job) { return `<div class="card detail-card"><div class="badge-row">${renderBadge(job.subtitles.status)}${renderBadge("자막 스타일")}</div><p class="body-md">스타일: ${escapeHtml(job.subtitles.style)}</p><p class="body-md">강조 규칙: ${escapeHtml(job.subtitles.emphasis)}</p><div class="stack">${job.subtitles.sample.map((line) => `<div class="quote">${escapeHtml(line)}</div>`).join("")}</div></div>`; }
function renderDeliverablesTab(job) { return `<div class="result-grid">${job.deliverables.map((item) => `<div class="card result-card"><div class="badge-row">${renderBadge(item.status)}</div><h3 class="title-md">${escapeHtml(item.label)}</h3><p class="body-md">${escapeHtml(item.note)}</p></div>`).join("")}</div>`; }
function renderLogTab(job) { return `<div class="card detail-card"><div class="timeline">${job.logs.map((log) => `<div class="timeline-item"><div class="badge-row">${renderBadge(log.time)}</div><h3 class="title-md">${escapeHtml(log.title)}</h3><p class="body-md">${escapeHtml(log.detail)}</p></div>`).join("")}</div></div>`; }
function renderDetailTab(job) { return ({ 개요: renderOverviewTab, 스크립트: renderScriptTab, 보이스: renderVoiceTab, 자막: renderSubtitleTab, 결과물: renderDeliverablesTab, 로그: renderLogTab }[state.activeTab])(job); }

function renderJobDetailScreen() {
  const job = getSelectedJob();
  if (!job || job.status !== "완료") {
    return `<main class="screen">${renderTopbar({ title: "작업 상세", subtitle: "완료 티켓 전용", backRoute: "job-list", rightContent: renderBadge("읽기 전용") })}<section class="section"><div class="card card-padding stack"><h2 class="title-lg">상세 탭은 생성 완료 티켓만 확인할 수 있습니다.</h2><p class="body-md">생성 중인 티켓은 단계형 위저드에서 계속 진행해 주세요.</p><button class="button button-primary" type="button" data-action="navigate" data-route="ticket-link">위저드로 이동</button></div></section></main>`;
  }
  return `<main class="screen">${renderTopbar({ title: "작업 상세", subtitle: job.id, backRoute: "job-list", rightContent: renderBadge("완료 티켓") })}<section class="hero-card card card-padding stack"><div class="badge-row">${job.tags.map(renderBadge).join("")}</div><h2 class="title-lg">${escapeHtml(job.title)}</h2><p class="body-md">${escapeHtml(job.partner)} · ${escapeHtml(job.channel)} · 마감 ${escapeHtml(job.dueLabel)}</p>${renderProgress(job.progress)}</section><section class="section"><div class="tab-row" aria-label="상세 탭">${DETAIL_TABS.map((tab) => `<button class="pill ${state.activeTab === tab ? "is-active" : ""}" type="button" data-action="set-tab" data-tab="${tab}">${escapeHtml(tab)}</button>`).join("")}</div>${renderDetailTab(job)}</section></main>`;
}

function renderScreen() {
  if (!state.authenticated && state.route !== "login") state.route = "login";
  switch (state.route) {
    case "dashboard": return renderDashboardScreen();
    case "job-list": return renderJobListScreen();
    case "job-detail": return renderJobDetailScreen();
    case "ticket-link":
    case "ticket-download":
    case "ticket-keyword":
    case "ticket-partners-link":
    case "ticket-analysis":
    case "ticket-script":
    case "ticket-voice":
    case "ticket-subtitle":
    case "ticket-result":
      return renderWizardScreen();
    case "login":
    default: return renderLoginScreen();
  }
}

function render() { root.innerHTML = `<div class="app-stage"><div class="phone-shell">${renderScreen()}${state.authenticated ? renderBottomNav() : ""}</div></div>`; }

function navigate(route) {
  if (route === "login") state.authenticated = false;
  else if (!state.authenticated) state.authenticated = true;
  if (route !== "job-detail") state.activeTab = "개요";
  state.wizardError = "";
  state.route = route;
  render();
}

function validateLinkStep(form) {
  const sourceLink = form.get("sourceLink")?.toString().trim() || "";
  if (!sourceLink) return { ok: false, message: "링크를 입력해 주세요." };
  const platform = detectPlatform(sourceLink);
  if (!platform) return { ok: false, message: "지원되지 않는 플랫폼 링크입니다. (유튜브/인스타그램/틱톡만 지원)" };
  return { ok: true, sourceLink, platform: platform.label };
}

function validateKeywordStep(form) {
  const keywords = form.get("keywords")?.toString().trim() || "";
  if (!keywords) return { ok: false, message: "키워드를 1개 이상 입력해 주세요." };
  return { ok: true, keywords };
}

function completeTicketFromDraft() {
  const idx = String(state.jobs.length + 1).padStart(2, "0");
  const keywordList = state.ticketDraft.keywords.split(",").map((v) => v.trim()).filter(Boolean);
  const today = "2026.03.22";
  const job = {
    id: `JOB-260322-${idx}`,
    partner: "신규 파트너",
    title: `${state.ticketDraft.platform} 소스 기반 자동 생성 티켓`,
    status: "완료",
    progress: 100,
    dueLabel: "완료됨",
    channel: state.ticketDraft.platform,
    createdAt: today,
    owner: "워크플로우 봇",
    priority: "중간",
    tags: ["생성 완료", ...keywordList.slice(0, 2)],
    overview: {
      summary: state.ticketDraft.resultSummary,
      goal: state.ticketDraft.analysisDraft,
      notes: ["링크 기반 자동 흐름 완료", "검증 규칙 통과", "완료 탭 전용으로 이동"],
    },
    script: { headline: "AI 생성 스크립트", body: [state.ticketDraft.scriptDraft], cta: state.ticketDraft.partnersLink, status: "승인 완료" },
    voice: { talent: "AI Voice", mood: "안정형", speed: "1.00x", pitch: "0", memo: state.ticketDraft.voiceStatus, status: "완료" },
    subtitles: { style: "자동 자막 스타일", emphasis: "핵심 키워드 중심", sample: keywordList.map((k) => `${k} 강조 자막`), status: "완료" },
    deliverables: [
      { label: "최종 MP4", note: "자동 파이프라인 완료", status: "완료" },
      { label: "파트너스 링크", note: state.ticketDraft.partnersLink, status: "완료" },
    ],
    logs: [
      { time: "방금", title: "워크플로우 완료", detail: "단계형 생성 위저드를 모두 통과했습니다." },
      { time: "방금", title: "상세 탭 전환", detail: "생성 완료 티켓 보기로 이동합니다." },
    ],
  };
  state.jobs.unshift(job);
  state.selectedJobId = job.id;
  state.ticketDraft = initialTicketDraft();
  state.route = "job-detail";
  state.activeTab = "개요";
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const { action } = target.dataset;

  if (action === "navigate") { navigate(target.dataset.route); return; }
  if (action === "open-job") { state.selectedJobId = target.dataset.jobId; state.route = "job-detail"; state.activeTab = "개요"; state.authenticated = true; render(); return; }
  if (action === "set-tab") { state.activeTab = target.dataset.tab; render(); return; }
  if (action === "set-filter") { state.statusFilter = target.dataset.filter; render(); return; }

  if (action === "download-progress") {
    state.ticketDraft.downloadProgress = Math.min(100, state.ticketDraft.downloadProgress + 25);
    state.wizardError = "";
    render();
    return;
  }

  if (action === "goto-step") {
    if (target.dataset.route === "ticket-keyword" && state.ticketDraft.downloadProgress < 100) {
      state.wizardError = "다운로드가 완료되어야 다음 단계로 이동할 수 있습니다.";
      render();
      return;
    }
    navigate(target.dataset.route);
    return;
  }

  if (action === "generate-partners-link") {
    state.ticketDraft.partnersLink = `https://partners.kikit.co/r/${Date.now().toString().slice(-6)}`;
    navigate("ticket-analysis");
    return;
  }
  if (action === "generate-analysis") {
    state.ticketDraft.analysisDraft = `${state.ticketDraft.platform} 원본을 분석한 결과, ${state.ticketDraft.keywords} 키워드 중심의 후킹 구성이 적합합니다.`;
    navigate("ticket-script");
    return;
  }
  if (action === "generate-script") {
    state.ticketDraft.scriptDraft = `첫 3초에 ${state.ticketDraft.keywords.split(",")[0]?.trim() || "핵심 메시지"}를 강조하고, 후반부에서 파트너스 링크 클릭을 유도합니다.`;
    navigate("ticket-voice");
    return;
  }
  if (action === "generate-voice") {
    state.ticketDraft.voiceStatus = "보이스 합성 완료 (여성 톤, 1.0x)";
    navigate("ticket-subtitle");
    return;
  }
  if (action === "generate-subtitle") {
    state.ticketDraft.subtitleStatus = "자막 합성 완료 (자동 줄바꿈 적용)";
    state.ticketDraft.resultSummary = "최종 결과물 준비가 완료되었습니다. 상세 탭에서 결과를 확인할 수 있습니다.";
    navigate("ticket-result");
    return;
  }
  if (action === "complete-ticket") {
    completeTicketFromDraft();
    render();
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement)) return;
  if (target.dataset.role === "job-search") { state.searchQuery = target.value; render(); }
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();

  if (form.id === "login-form") { state.authenticated = true; state.route = "dashboard"; render(); return; }

  if (form.id === "ticket-link-form") {
    const result = validateLinkStep(new FormData(form));
    if (!result.ok) { state.wizardError = result.message; render(); return; }
    state.ticketDraft = { ...initialTicketDraft(), sourceLink: result.sourceLink, platform: result.platform, downloadProgress: 0 };
    navigate("ticket-download");
    return;
  }

  if (form.id === "ticket-keyword-form") {
    const result = validateKeywordStep(new FormData(form));
    if (!result.ok) { state.wizardError = result.message; render(); return; }
    state.ticketDraft.keywords = result.keywords;
    state.ticketDraft.partnersLink = `https://partners.kikit.co/new?kw=${encodeURIComponent(result.keywords)}`;
    navigate("ticket-partners-link");
  }
});

render();
