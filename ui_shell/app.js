const DETAIL_TABS = ["개요", "스크립트", "보이스", "자막", "결과물", "로그"];

const mockJobs = [
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

const initialDraft = () => ({
  partner: "",
  contentType: "릴스 광고",
  channel: "인스타 릴스",
  tone: "프리미엄 미니멀",
  dueDate: "2026-03-24",
  memo: "",
});

const state = {
  route: "login",
  authenticated: false,
  activeTab: "개요",
  selectedJobId: mockJobs[0].id,
  statusFilter: "전체",
  searchQuery: "",
  createDraft: initialDraft(),
};

function sentenceSplit(text) {
  return String(text || "")
    .split(/(?<=[.!?。！？\n])\s+|\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function makeClockLabel() {
  return new Date().toTimeString().slice(0, 5);
}

function appendTicketLog(job, title, detail, level = "info") {
  job.logs.unshift({
    time: makeClockLabel(),
    title,
    detail,
    level,
  });
}

function hydrateJob(job) {
  const scriptSeed = [job.script?.headline, ...(job.script?.body || [])].filter(Boolean).join(". ");
  const seededText = (job.voice_script_text || scriptSeed || "").trim();
  const lines = sentenceSplit(seededText);
  const estDuration = Math.max(2, Number((seededText.length / 9).toFixed(2)));

  job.voice_script_text = seededText;
  job.sourceVideoPath = job.sourceVideoPath || `videos/${job.id}.mp4`;
  job.generatedAudioPath = job.generatedAudioPath || "";
  job.finalRenderPath = job.finalRenderPath || "";
  job.pipelineStatus = job.pipelineStatus || "대기";
  job.pipelineError = job.pipelineError || "";
  job.subtitleSegments = job.subtitleSegments || lines.map((text, index) => ({
    index: index + 1,
    start: Number((index * (estDuration / Math.max(lines.length, 1))).toFixed(2)),
    end: Number(((index + 1) * (estDuration / Math.max(lines.length, 1))).toFixed(2)),
    text,
  }));
}

mockJobs.forEach(hydrateJob);

const root = document.querySelector("#app");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function badgeTone(label) {
  if (["진행 중", "높음", "검수 대기", "렌더링 대기", "녹음 예약", "작성 중"].includes(label)) {
    return "badge-rose";
  }

  if (["완료", "완료됨", "승인 완료"].includes(label)) {
    return "badge-ink";
  }

  return "badge-soft";
}

function renderBadge(label) {
  return `<span class="badge ${badgeTone(label)}">${escapeHtml(label)}</span>`;
}

function renderTopbar({ title, subtitle, backRoute, rightContent = "" }) {
  const leading = backRoute
    ? `<button class="icon-button" type="button" data-action="navigate" data-route="${backRoute}" aria-label="이전 화면">←</button>`
    : `<div class="avatar">KP</div>`;

  return `
    <header class="topbar">
      <div class="topbar-side">${leading}</div>
      <div class="topbar-main">
        <p class="label">${escapeHtml(subtitle)}</p>
        <h1 class="title-lg">${escapeHtml(title)}</h1>
      </div>
      <div class="topbar-side">${rightContent}</div>
    </header>
  `;
}

function renderSectionHeader(kicker, title, actionLabel = "", actionRoute = "") {
  const action = actionLabel && actionRoute
    ? `<button class="ghost-button" type="button" data-action="navigate" data-route="${actionRoute}">${escapeHtml(actionLabel)}</button>`
    : "";

  return `
    <div class="section-header">
      <div class="section-copy">
        <p class="label">${escapeHtml(kicker)}</p>
        <h2 class="title-md">${escapeHtml(title)}</h2>
      </div>
      ${action}
    </div>
  `;
}

function renderProgress(value) {
  return `
    <div class="progress-bar" aria-hidden="true">
      <div class="progress-value" style="width: ${Math.max(0, Math.min(100, value))}%"></div>
    </div>
  `;
}

function renderMenuTile(title, note, route) {
  return `
    <button class="menu-tile card-inset" type="button" data-action="navigate" data-route="${route}">
      <span class="menu-kicker">${escapeHtml(title)}</span>
      <p class="body-sm">${escapeHtml(note)}</p>
    </button>
  `;
}

function renderInfoCard(label, value) {
  return `
    <div class="info-card">
      <p class="label">${escapeHtml(label)}</p>
      <span class="info-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderJobCard(job) {
  return `
    <button class="card job-card" type="button" data-action="open-job" data-job-id="${job.id}">
      <div class="job-card-header">
        <div class="job-card-title">
          <div class="badge-row">
            ${renderBadge(job.status)}
            ${renderBadge(job.channel)}
          </div>
          <h3 class="title-md">${escapeHtml(job.title)}</h3>
          <p class="body-md">${escapeHtml(job.partner)} · ${escapeHtml(job.id)}</p>
        </div>
        ${renderBadge(job.priority)}
      </div>
      <div class="job-card-title">
        <div class="meta-row">
          <span class="helper-note">마감 ${escapeHtml(job.dueLabel)}</span>
          <span class="helper-note">담당 ${escapeHtml(job.owner)}</span>
        </div>
        ${renderProgress(job.progress)}
        <div class="meta-row">
          <p class="body-sm">스크립트 ${escapeHtml(job.script.status)}</p>
          <p class="body-sm">자막 ${escapeHtml(job.subtitles.status)}</p>
        </div>
      </div>
    </button>
  `;
}

function renderBottomNav() {
  const items = [
    { label: "대시보드", route: "dashboard" },
    { label: "작업 목록", route: "job-list" },
    { label: "작업 생성", route: "create-job" },
    { label: "상세 보기", route: "job-detail" },
  ];

  return `
    <div class="bottom-nav-wrap">
      <nav class="bottom-nav" aria-label="주요 메뉴">
        ${items.map((item) => `
          <button
            type="button"
            class="${state.route === item.route ? "is-active" : ""}"
            data-action="navigate"
            data-route="${item.route}"
          >
            ${escapeHtml(item.label)}
          </button>
        `).join("")}
      </nav>
    </div>
  `;
}

function renderLoginScreen() {
  return `
    <main class="screen screen-login">
      <div class="lockup">
        <span class="eyebrow">모바일 퍼스트 목업</span>
        <h1 class="title-xl">키킷 파트너스 스튜디오</h1>
        <p class="body-lg">한글 메뉴 중심의 프리미엄 미니멀 셸입니다. 프로그램 이제 시작해보자.</p>
      </div>

      <div class="hero-card card card-padding stack">
        <div class="badge-row">
          ${renderBadge("로그인")}
          ${renderBadge("목업 데이터")}
        </div>
        <h2 class="title-lg">시작 전, 팀 공간에 들어가기</h2>
        <p class="body-md">실제 백엔드는 아직 연결하지 않고, 승인된 모바일 흐름만 먼저 확인할 수 있도록 구성했습니다.</p>
      </div>

      <form id="login-form" class="card card-padding stack">
        <label class="input-wrap">
          <span class="label">이메일</span>
          <input class="input" type="email" name="email" placeholder="team@kikitpartners.co" value="studio@kikitpartners.co" autocomplete="email">
        </label>
        <label class="input-wrap">
          <span class="label">비밀번호</span>
          <input class="input" type="password" name="password" placeholder="비밀번호를 입력하세요" value="••••••••" autocomplete="current-password">
        </label>
        <div class="pill-row">
          <span class="helper-note">모바일 최적화</span>
          <span class="helper-note">화이트 / 소프트 핑크</span>
        </div>
        <button class="button button-primary" type="submit">시작하기</button>
      </form>

      <div class="card card-padding stack">
        <p class="label">바로 확인할 메뉴</p>
        <div class="menu-grid">
          ${renderMenuTile("대시보드", "오늘 진행 상황을 한 번에 확인", "dashboard")}
          ${renderMenuTile("작업 생성", "새 작업을 빠르게 등록", "create-job")}
          ${renderMenuTile("작업 목록", "전체 작업 상태를 스캔", "job-list")}
          ${renderMenuTile("상세 보기", "탭 기반 세부 셸 확인", "job-detail")}
        </div>
      </div>
    </main>
  `;
}

function renderDashboardScreen() {
  const activeJobs = mockJobs.filter((job) => job.status === "진행 중").length;
  const reviewJobs = mockJobs.filter((job) => job.script.status === "검수 대기").length;
  const doneJobs = mockJobs.filter((job) => job.status === "완료").length;
  const todayJobs = mockJobs.filter((job) => job.dueLabel.includes("오늘")).length;

  return `
    <main class="screen">
      ${renderTopbar({
        title: "대시보드",
        subtitle: "오늘의 작업 흐름",
        rightContent: '<span class="helper-note">목업 모드</span>',
      })}

      <section class="hero-card card card-padding stack">
        <div class="badge-row">
          ${renderBadge("운영 허브")}
          ${renderBadge("모바일 우선")}
        </div>
        <h2 class="title-lg">지금 확인해야 할 작업이 또렷하게 보이도록 정리했어요.</h2>
        <p class="body-md">복잡한 관리자 레이아웃 대신, 손가락 한 번으로 이동할 수 있는 시작 화면에 집중했습니다.</p>
        <div class="button-row">
          <button class="button button-primary" type="button" data-action="navigate" data-route="create-job">새 작업 만들기</button>
          <button class="button button-secondary" type="button" data-action="navigate" data-route="job-list">작업 목록 보기</button>
        </div>
      </section>

      <section class="section">
        ${renderSectionHeader("오늘 요약", "핵심 지표")}
        <div class="stat-grid">
          <div class="stat-card"><span class="metric-value">${activeJobs}건</span><p class="body-sm">진행 중 작업</p></div>
          <div class="stat-card"><span class="metric-value">${todayJobs}건</span><p class="body-sm">오늘 마감</p></div>
          <div class="stat-card"><span class="metric-value">${reviewJobs}건</span><p class="body-sm">검수 대기</p></div>
          <div class="stat-card"><span class="metric-value">${doneJobs}건</span><p class="body-sm">완료 작업</p></div>
        </div>
      </section>

      <section class="section">
        ${renderSectionHeader("빠른 메뉴", "바로 가기")}
        <div class="menu-grid">
          ${renderMenuTile("작업 생성", "요청 내용을 입력하고 셸 생성", "create-job")}
          ${renderMenuTile("작업 목록", "상태별로 빠르게 스캔", "job-list")}
          ${renderMenuTile("상세 보기", "탭 UI와 로그 흐름 확인", "job-detail")}
          ${renderMenuTile("로그인 화면", "처음 시작 화면 다시 보기", "login")}
        </div>
      </section>

      <section class="section">
        ${renderSectionHeader("최근 작업", "우선 확인 2건", "전체 보기", "job-list")}
        <div class="job-list">
          ${mockJobs.slice(0, 2).map(renderJobCard).join("")}
        </div>
      </section>
    </main>
  `;
}

function renderCreateScreen() {
  return `
    <main class="screen">
      ${renderTopbar({
        title: "작업 생성",
        subtitle: "새 작업 등록",
        backRoute: "dashboard",
        rightContent: renderBadge("목업 저장"),
      })}

      <section class="hero-card card card-padding stack">
        <div class="badge-row">
          ${renderBadge("한글 폼")}
          ${renderBadge("모바일 입력 최적화")}
        </div>
        <h2 class="title-lg">필수 정보만 간결하게 입력하고 바로 작업을 시작합니다.</h2>
        <p class="body-md">실제 저장은 하지 않고, 입력값을 기준으로 새로운 목업 작업 카드를 만들어 상세 화면으로 이동합니다.</p>
      </section>

      <form id="job-create-form" class="section">
        <div class="card card-padding form-grid">
          <label class="input-wrap">
            <span class="label">파트너명</span>
            <input class="input" type="text" name="partner" value="${escapeHtml(state.createDraft.partner)}" placeholder="예: 클린뷰">
          </label>

          <label class="input-wrap">
            <span class="label">콘텐츠 유형</span>
            <select class="select" name="contentType">
              ${["릴스 광고", "제품 티저", "리마인드 영상", "후기 숏폼"].map((option) => `
                <option value="${option}" ${state.createDraft.contentType === option ? "selected" : ""}>${option}</option>
              `).join("")}
            </select>
          </label>

          <label class="input-wrap">
            <span class="label">게시 채널</span>
            <select class="select" name="channel">
              ${["인스타 릴스", "틱톡", "유튜브 쇼츠"].map((option) => `
                <option value="${option}" ${state.createDraft.channel === option ? "selected" : ""}>${option}</option>
              `).join("")}
            </select>
          </label>

          <label class="input-wrap">
            <span class="label">보이스 톤</span>
            <select class="select" name="tone">
              ${["프리미엄 미니멀", "따뜻한 설득형", "빠르고 선명한 톤", "세련된 무드형"].map((option) => `
                <option value="${option}" ${state.createDraft.tone === option ? "selected" : ""}>${option}</option>
              `).join("")}
            </select>
          </label>

          <label class="input-wrap">
            <span class="label">마감일</span>
            <input class="input" type="date" name="dueDate" value="${escapeHtml(state.createDraft.dueDate)}">
          </label>

          <label class="input-wrap">
            <span class="label">요청 메모</span>
            <textarea class="textarea" name="memo" placeholder="핵심 메시지, 레퍼런스, 꼭 지켜야 할 포인트를 적어주세요.">${escapeHtml(state.createDraft.memo)}</textarea>
          </label>
        </div>

        <div class="card detail-card sticky-bar">
          <div class="badge-row">
            ${renderBadge("목업 데이터로 생성")}
            ${renderBadge("백엔드 미연동")}
          </div>
          <p class="body-md">저장 버튼을 누르면 입력값 기반의 새 작업 카드가 생성되고 바로 상세 탭 셸로 이동합니다.</p>
          <button class="button button-primary" type="submit">작업 생성하기</button>
        </div>
      </form>
    </main>
  `;
}

function getFilteredJobs() {
  return mockJobs.filter((job) => {
    const matchesFilter = state.statusFilter === "전체"
      || job.status === state.statusFilter
      || job.script.status === state.statusFilter;
    const haystack = `${job.title} ${job.partner} ${job.channel}`.toLowerCase();
    const matchesSearch = !state.searchQuery || haystack.includes(state.searchQuery.trim().toLowerCase());

    return matchesFilter && matchesSearch;
  });
}

function renderJobListScreen() {
  const filters = ["전체", "진행 중", "검수 대기", "완료"];
  const filteredJobs = getFilteredJobs();

  return `
    <main class="screen">
      ${renderTopbar({
        title: "작업 목록",
        subtitle: `전체 ${mockJobs.length}건`,
        backRoute: "dashboard",
        rightContent: '<span class="helper-note">필터 가능</span>',
      })}

      <section class="stack">
        <div class="search-wrap">
          <input
            class="search-input"
            type="search"
            data-role="job-search"
            placeholder="작업명, 파트너명, 채널 검색"
            value="${escapeHtml(state.searchQuery)}"
          >
        </div>

        <div class="pill-row" aria-label="상태 필터">
          ${filters.map((filter) => `
            <button class="pill ${state.statusFilter === filter ? "is-active" : ""}" type="button" data-action="set-filter" data-filter="${filter}">
              ${escapeHtml(filter)}
            </button>
          `).join("")}
        </div>
      </section>

      <section class="section">
        ${renderSectionHeader("작업 카드", "모바일 스캔 리스트", "새 작업", "create-job")}
        <div class="job-list">
          ${filteredJobs.length
            ? filteredJobs.map(renderJobCard).join("")
            : `
              <div class="card card-padding stack">
                <h3 class="title-md">조건에 맞는 작업이 없습니다.</h3>
                <p class="body-md">검색어나 상태 필터를 조정해 보세요.</p>
              </div>
            `}
        </div>
      </section>
    </main>
  `;
}

function getSelectedJob() {
  return mockJobs.find((job) => job.id === state.selectedJobId) || mockJobs[0];
}

function renderOverviewTab(job) {
  return `
    <div class="stack">
      <div class="card detail-card">
        <div class="badge-row">
          ${renderBadge(job.status)}
          ${renderBadge(job.channel)}
          ${renderBadge(job.script.status)}
        </div>
        <p class="body-md">${escapeHtml(job.overview.summary)}</p>
        <div class="info-grid">
          ${renderInfoCard("파트너", job.partner)}
          ${renderInfoCard("담당 팀", job.owner)}
          ${renderInfoCard("마감", job.dueLabel)}
          ${renderInfoCard("생성일", job.createdAt)}
        </div>
      </div>

      <div class="card detail-card">
        <h3 class="title-md">핵심 목표</h3>
        <p class="body-md">${escapeHtml(job.overview.goal)}</p>
        <ul class="bullet-list">
          ${job.overview.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
        </ul>
      </div>
    </div>
  `;
}

function renderScriptTab(job) {
  return `
    <div class="stack">
      <div class="card script-block">
        <div class="badge-row">
          ${renderBadge(job.script.status)}
          ${renderBadge("스크립트 셸")}
        </div>
        <h3 class="title-md">${escapeHtml(job.script.headline)}</h3>
        <div class="quote">
          ${job.script.body.map((line) => `<p class="body-md">${escapeHtml(line)}</p>`).join("")}
        </div>
      </div>

      <div class="card detail-card">
        <h3 class="title-md">콜 투 액션</h3>
        <p class="body-md">${escapeHtml(job.script.cta)}</p>
      </div>
    </div>
  `;
}

function runVoicePipeline(job, { retry = false } = {}) {
  const voiceScriptText = String(job.voice_script_text || "").trim();
  appendTicketLog(job, retry ? "재시도 시작" : "파이프라인 시작", "보이스/자막/최종 렌더 통합 파이프라인을 시작합니다.");

  if (!voiceScriptText) {
    job.pipelineStatus = "실패";
    job.pipelineError = "voice_script_text가 비어 있어 ElevenLabs 입력을 만들 수 없습니다.";
    appendTicketLog(job, "실패", job.pipelineError, "error");
    return;
  }

  if (!job.sourceVideoPath) {
    job.pipelineStatus = "실패";
    job.pipelineError = "원본 영상 경로가 없어 FFmpeg 합성을 진행할 수 없습니다.";
    appendTicketLog(job, "실패", job.pipelineError, "error");
    return;
  }

  job.pipelineStatus = "실행 중";
  job.pipelineError = "";

  const charDuration = Math.max(2.5, Number((voiceScriptText.length / 8.7).toFixed(2)));
  const sentences = sentenceSplit(voiceScriptText);

  job.generatedAudioPath = `audios/${job.id}_${Date.now()}.mp3`;
  appendTicketLog(job, "TTS 완료", `ElevenLabs 입력에 voice_script_text를 사용해 오디오를 생성했습니다. (${job.generatedAudioPath})`);

  let cursor = 0;
  job.subtitleSegments = sentences.map((text, index) => {
    const weight = Math.max(1, text.length);
    const duration = Number(((charDuration * weight) / Math.max(voiceScriptText.length, 1)).toFixed(2));
    const start = Number(cursor.toFixed(2));
    const end = Number((cursor + duration).toFixed(2));
    cursor = end;
    return { index: index + 1, start, end, text };
  });
  appendTicketLog(job, "자막 생성", `${job.subtitleSegments.length}개 문장 세그먼트를 음성 길이 타임스탬프로 생성했습니다.`);

  job.finalRenderPath = `done/${job.id}/final_${job.id}.mp4`;
  job.pipelineStatus = "완료";
  job.status = "완료";
  job.progress = 100;
  job.voice.status = "보이스 완료";
  job.subtitles.status = "자동 생성 완료";

  const subtitlePreview = `tmp/${job.id}.srt`;
  appendTicketLog(
    job,
    "FFmpeg 합성 완료",
    `원본영상(${job.sourceVideoPath}) + 생성오디오(${job.generatedAudioPath}) + 자막(${subtitlePreview})을 합성해 ${job.finalRenderPath} 생성`,
  );
}

function renderVoiceTab(job) {
  return `
    <div class="stack">
      <div class="card detail-card">
        <div class="badge-row">
          ${renderBadge(job.voice.status)}
          ${renderBadge(job.voice.talent)}
        </div>
        <div class="info-grid">
          ${renderInfoCard("톤", job.voice.mood)}
          ${renderInfoCard("속도", job.voice.speed)}
          ${renderInfoCard("피치", job.voice.pitch)}
          ${renderInfoCard("메모", job.voice.memo)}
        </div>
      </div>

      <div class="card detail-card stack">
        <h3 class="title-md">voice_script_text</h3>
        <p class="body-sm">티켓에 저장되며 ElevenLabs 입력으로 바로 사용됩니다.</p>
        <textarea
          class="textarea"
          data-role="voice-script-text"
          data-job-id="${job.id}"
          placeholder="보이스 스크립트를 입력하세요."
        >${escapeHtml(job.voice_script_text || "")}</textarea>
        <div class="badge-row">
          ${renderBadge(`파이프라인 ${job.pipelineStatus || "대기"}`)}
          ${job.generatedAudioPath ? renderBadge(`오디오 경로 저장`) : renderBadge("오디오 미생성")}
        </div>
        <button class="button button-primary" type="button" data-action="run-pipeline" data-job-id="${job.id}">
          보이스/자막/렌더 파이프라인 실행
        </button>
      </div>
    </div>
  `;
}

function renderSubtitleTab(job) {
  return `
    <div class="stack">
      <div class="card detail-card">
        <div class="badge-row">
          ${renderBadge(job.subtitles.status)}
          ${renderBadge("자막 스타일")}
        </div>
        <p class="body-md">스타일: ${escapeHtml(job.subtitles.style)}</p>
        <p class="body-md">강조 규칙: ${escapeHtml(job.subtitles.emphasis)}</p>
        <div class="stack">
          ${job.subtitles.sample.map((line) => `<div class="quote">${escapeHtml(line)}</div>`).join("")}
        </div>
      </div>
      <div class="card detail-card">
        <h3 class="title-md">타임스탬프 세그먼트</h3>
        <div class="stack">
          ${(job.subtitleSegments || []).map((seg) => `
            <div class="quote">[${seg.start.toFixed(2)}s - ${seg.end.toFixed(2)}s] ${escapeHtml(seg.text)}</div>
          `).join("") || '<p class="body-md">아직 생성된 자막이 없습니다.</p>'}
        </div>
      </div>
    </div>
  `;
}

function renderDeliverablesTab(job) {
  return `
    <div class="stack">
      <div class="result-grid">
        ${job.deliverables.map((item) => `
          <div class="card result-card">
            <div class="badge-row">${renderBadge(item.status)}</div>
            <h3 class="title-md">${escapeHtml(item.label)}</h3>
            <p class="body-md">${escapeHtml(item.note)}</p>
          </div>
        `).join("")}
      </div>
      <div class="card detail-card stack">
        <h3 class="title-md">최종 렌더 상태</h3>
        <p class="body-md">원본 영상: ${escapeHtml(job.sourceVideoPath || "-")}</p>
        <p class="body-md">생성 오디오: ${escapeHtml(job.generatedAudioPath || "-")}</p>
        <p class="body-md">최종 MP4: ${escapeHtml(job.finalRenderPath || "-")}</p>
        ${job.pipelineError ? `<p class="body-md">실패 원인: ${escapeHtml(job.pipelineError)}</p>` : ""}
        ${job.pipelineStatus === "실패"
          ? `<button class="button button-secondary" type="button" data-action="retry-pipeline" data-job-id="${job.id}">실패 단계 재시도</button>`
          : ""}
      </div>
    </div>
  `;
}

function renderLogTab(job) {
  return `
    <div class="card detail-card">
      <div class="timeline">
        ${job.logs.map((log) => `
          <div class="timeline-item">
            <div class="badge-row">${renderBadge(log.time)}</div>
            <h3 class="title-md">${escapeHtml(log.title)}</h3>
            <p class="body-md">${escapeHtml(log.detail)}</p>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderDetailTab(job) {
  const renderers = {
    개요: renderOverviewTab,
    스크립트: renderScriptTab,
    보이스: renderVoiceTab,
    자막: renderSubtitleTab,
    결과물: renderDeliverablesTab,
    로그: renderLogTab,
  };

  return renderers[state.activeTab](job);
}

function renderJobDetailScreen() {
  const job = getSelectedJob();

  return `
    <main class="screen">
      ${renderTopbar({
        title: "작업 상세",
        subtitle: job.id,
        backRoute: "job-list",
        rightContent: renderBadge("탭 셸"),
      })}

      <section class="hero-card card card-padding stack">
        <div class="badge-row">${job.tags.map(renderBadge).join("")}</div>
        <h2 class="title-lg">${escapeHtml(job.title)}</h2>
        <p class="body-md">${escapeHtml(job.partner)} · ${escapeHtml(job.channel)} · 마감 ${escapeHtml(job.dueLabel)}</p>
        ${renderProgress(job.progress)}
        <div class="meta-row">
          <span class="helper-note">진행률 ${job.progress}%</span>
          <span class="helper-note">${escapeHtml(job.voice.status)}</span>
          <span class="helper-note">${escapeHtml(job.subtitles.status)}</span>
        </div>
      </section>

      <section class="section">
        <div class="tab-row" aria-label="상세 탭">
          ${DETAIL_TABS.map((tab) => `
            <button class="pill ${state.activeTab === tab ? "is-active" : ""}" type="button" data-action="set-tab" data-tab="${tab}">
              ${escapeHtml(tab)}
            </button>
          `).join("")}
        </div>
        ${renderDetailTab(job)}
      </section>
    </main>
  `;
}

function renderScreen() {
  if (!state.authenticated && state.route !== "login") {
    state.route = "login";
  }

  switch (state.route) {
    case "dashboard":
      return renderDashboardScreen();
    case "create-job":
      return renderCreateScreen();
    case "job-list":
      return renderJobListScreen();
    case "job-detail":
      return renderJobDetailScreen();
    case "login":
    default:
      return renderLoginScreen();
  }
}

function render() {
  root.innerHTML = `
    <div class="app-stage">
      <div class="phone-shell">
        ${renderScreen()}
        ${state.authenticated ? renderBottomNav() : ""}
      </div>
    </div>
  `;
}

function navigate(route) {
  if (route === "login") {
    state.authenticated = false;
  } else if (!state.authenticated) {
    state.authenticated = true;
  }

  if (route !== "job-detail") {
    state.activeTab = "개요";
  }

  state.route = route;
  render();
}

function createMockJob(form) {
  const partner = form.get("partner")?.toString().trim() || "새 파트너";
  const contentType = form.get("contentType")?.toString().trim() || "릴스 광고";
  const channel = form.get("channel")?.toString().trim() || "인스타 릴스";
  const tone = form.get("tone")?.toString().trim() || "프리미엄 미니멀";
  const dueDate = form.get("dueDate")?.toString().trim() || "2026-03-24";
  const memo = form.get("memo")?.toString().trim() || "핵심 메시지를 아직 입력하지 않았습니다.";
  const lastIndex = String(mockJobs.length + 1).padStart(2, "0");

  const newJob = {
    id: `JOB-260322-${lastIndex}`,
    partner,
    title: `${partner} ${contentType}`,
    status: "진행 중",
    progress: 16,
    dueLabel: dueDate.replaceAll("-", "."),
    channel,
    createdAt: "2026.03.22",
    owner: "운영 신작업",
    priority: "높음",
    tags: ["신규 생성", tone],
    overview: {
      summary: `${partner}용 ${contentType} 작업이 새로 시작되었습니다.`,
      goal: memo,
      notes: [
        "실제 저장 없이 셸 화면만 우선 구성됨",
        "다음 단계에서 백엔드 필드 매핑 가능",
        "모바일 기준 편집 흐름으로 이어질 수 있음",
      ],
    },
    script: {
      headline: `${partner}의 핵심 메시지를 담은 첫 스크립트 셸`,
      body: [
        "첫 장면에서 바로 관심을 끌 수 있는 후킹 문장을 배치합니다.",
        `${tone} 톤을 기준으로 전체 카피와 리듬을 맞춥니다.`,
        "최종 CTA는 실제 연결 전까지 목업 문구로 유지합니다.",
      ],
      cta: "지금 상세 검토로 넘어가기",
      status: "검수 대기",
    },
    voice: {
      talent: "기본 보이스",
      mood: tone,
      speed: "1.00x",
      pitch: "0",
      memo,
      status: "보이스 준비",
    },
    voice_script_text: memo || `${partner} ${contentType} 보이스 스크립트를 입력하세요.`,
    sourceVideoPath: `videos/JOB-260322-${lastIndex}.mp4`,
    generatedAudioPath: "",
    finalRenderPath: "",
    pipelineStatus: "대기",
    pipelineError: "",
    subtitleSegments: [],
    subtitles: {
      style: "화이트 베이스 + 소프트 핑크 포인트",
      emphasis: "핵심 메시지 위주 강조",
      sample: [
        `${partner} 작업이 방금 생성되었습니다.`,
        "다음 단계에서 스크립트와 자막을 구체화할 수 있습니다.",
      ],
      status: "초안",
    },
    deliverables: [
      { label: "세로형 MP4", note: "목업 결과물 준비 전", status: "대기" },
      { label: "썸네일", note: "대표 컷 미정", status: "대기" },
    ],
    logs: [
      { time: "지금", title: "새 작업 생성", detail: `${partner} ${contentType} 작업이 목업으로 추가되었습니다.` },
      { time: "다음", title: "세부 탭 준비", detail: "스크립트, 보이스, 자막, 결과물 탭 셸을 바로 확인할 수 있습니다." },
    ],
  };

  hydrateJob(newJob);
  mockJobs.unshift(newJob);
  state.selectedJobId = newJob.id;
  state.route = "job-detail";
  state.activeTab = "개요";
  state.searchQuery = "";
  state.statusFilter = "전체";
  state.createDraft = initialDraft();
  render();
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");

  if (!target) {
    return;
  }

  const { action } = target.dataset;

  if (action === "navigate") {
    navigate(target.dataset.route);
    return;
  }

  if (action === "open-job") {
    state.selectedJobId = target.dataset.jobId;
    state.route = "job-detail";
    state.activeTab = "개요";
    state.authenticated = true;
    render();
    return;
  }

  if (action === "set-tab") {
    state.activeTab = target.dataset.tab;
    render();
    return;
  }

  if (action === "set-filter") {
    state.statusFilter = target.dataset.filter;
    render();
    return;
  }

  if (action === "run-pipeline" || action === "retry-pipeline") {
    const job = mockJobs.find((item) => item.id === target.dataset.jobId);
    if (!job) return;
    runVoicePipeline(job, { retry: action === "retry-pipeline" });
    render();
  }
});

document.addEventListener("input", (event) => {
  const target = event.target;

  if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement)) {
    return;
  }

  if (target.dataset.role === "job-search") {
    state.searchQuery = target.value;
    render();
    return;
  }

  if (target.form?.id === "job-create-form" && target.name in state.createDraft) {
    state.createDraft[target.name] = target.value;
    return;
  }

  if (target.dataset.role === "voice-script-text") {
    const job = mockJobs.find((item) => item.id === target.dataset.jobId);
    if (!job) return;
    job.voice_script_text = target.value;
  }
});

document.addEventListener("submit", (event) => {
  const form = event.target;

  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  event.preventDefault();

  if (form.id === "login-form") {
    state.authenticated = true;
    state.route = "dashboard";
    render();
    return;
  }

  if (form.id === "job-create-form") {
    createMockJob(new FormData(form));
  }
});

render();
