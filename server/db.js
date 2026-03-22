const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'app.db');

const db = new sqlite3.Database(DB_PATH);

function run(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function onRun(err) {
      if (err) {
        reject(err);
        return;
      }
      resolve({ lastID: this.lastID, changes: this.changes });
    });
  });
}

function get(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(row);
    });
  });
}

function all(sql, params = []) {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(rows);
    });
  });
}

async function ensureColumn(tableName, columnName, columnDef) {
  const rows = await all(`PRAGMA table_info(${tableName})`);
  const hasColumn = rows.some((row) => row.name === columnName);
  if (!hasColumn) {
    await run(`ALTER TABLE ${tableName} ADD COLUMN ${columnName} ${columnDef}`);
  }
}

async function seedPromptProfiles() {
  const prompts = [
    {
      prompt_key: 'global_system_prompt',
      title: '글로벌 시스템 프롬프트',
      content: [
        '당신은 파트너스 운영 자동화 어시스턴트입니다.',
        '항상 JSON만 반환하고 한국어로 간결하게 답변하세요.',
        '추측이 필요한 경우 confidence를 낮추고 assumptions에 명시하세요.',
      ].join('\n'),
    },
    {
      prompt_key: 'inbox_parse_prompt',
      title: '인박스 파싱 프롬프트',
      content: [
        '수신 메시지에서 업무 항목을 추출하세요.',
        '필수 키: summary, category, priority, due_date, action_items[].',
        '정보가 부족하면 missing_fields 배열에 누락 필드를 넣으세요.',
      ].join('\n'),
    },
    {
      prompt_key: 'item_analysis_prompt',
      title: '항목 분석 프롬프트',
      content: [
        '업무 항목의 리스크, 예상 난이도, 권장 다음 행동을 분석하세요.',
        '필수 키: diagnosis, risk_level, impact, recommendations[], confidence.',
      ].join('\n'),
    },
    {
      prompt_key: 'automation_rule_prompt',
      title: '자동화 룰 초안 프롬프트',
      content: [
        '운영 정책에 맞는 자동화 룰 초안을 생성하세요.',
        '필수 키: rule_name, condition_text, category, status, approval_required, actions[].',
        'status는 draft 또는 proposed 중 하나여야 합니다.',
      ].join('\n'),
    },
    {
      prompt_key: 'dashboard_briefing_prompt',
      title: '대시보드 브리핑 프롬프트',
      content: [
        '대시보드 데이터를 한눈에 보는 브리핑으로 요약하세요.',
        '필수 키: headline, highlights[], risks[], next_actions[].',
      ].join('\n'),
    },
  ];

  for (const prompt of prompts) {
    await run(
      `INSERT INTO prompt_profiles (prompt_key, title, content)
       VALUES (?, ?, ?)
       ON CONFLICT(prompt_key) DO UPDATE SET
         title = excluded.title,
         content = excluded.content,
         updated_at = CURRENT_TIMESTAMP`,
      [prompt.prompt_key, prompt.title, prompt.content],
    );
  }
}

async function initDb() {
  await run(`CREATE TABLE IF NOT EXISTS prompt_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  await run(`CREATE TABLE IF NOT EXISTS ai_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_key TEXT,
    input_payload TEXT NOT NULL,
    output_payload TEXT NOT NULL,
    latency_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  await run(`CREATE TABLE IF NOT EXISTS automation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    action_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  await ensureColumn('automation_rules', 'condition_text', 'TEXT');
  await ensureColumn('automation_rules', 'category', "TEXT DEFAULT 'general'");
  await ensureColumn('automation_rules', 'status', "TEXT DEFAULT 'draft'");
  await ensureColumn('automation_rules', 'approval_required', 'INTEGER DEFAULT 1');
  await ensureColumn('automation_rules', 'created_by', "TEXT DEFAULT 'system'");

  await seedPromptProfiles();
}

async function getPromptByKey(promptKey) {
  return get('SELECT * FROM prompt_profiles WHERE prompt_key = ?', [promptKey]);
}

async function logAiRun({ endpoint, model, prompt_key, input_payload, output_payload, latency_ms }) {
  await run(
    `INSERT INTO ai_runs (endpoint, model, prompt_key, input_payload, output_payload, latency_ms)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [endpoint, model, prompt_key, JSON.stringify(input_payload), JSON.stringify(output_payload), latency_ms],
  );
}

module.exports = {
  db,
  run,
  get,
  all,
  initDb,
  getPromptByKey,
  logAiRun,
};
