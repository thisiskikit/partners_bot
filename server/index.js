const express = require('express');
const {
  initDb,
  getPromptByKey,
  listPromptProfiles,
  updatePromptProfile,
  logAiRun,
  all,
  saveAutomationRule,
} = require('./db');

const app = express();
const PORT = Number(process.env.PORT || 3000);
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';

app.use(express.json({ limit: '1mb' }));

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function sanitizeAnalyzeItemResult(result) {
  return {
    summary: String(result.summary || result.diagnosis || ''),
    best_interpretation: String(result.best_interpretation || result.diagnosis || ''),
    confidence: Number.isFinite(Number(result.confidence)) ? Number(result.confidence) : 0,
    suggested_actions: Array.isArray(result.suggested_actions)
      ? result.suggested_actions.map((action) => ({
          type: String(action?.type || 'noop'),
          label: String(action?.label || action?.reason || '확인 필요'),
          reason: action?.reason ? String(action.reason) : undefined,
          payload: isObject(action?.payload) ? action.payload : undefined,
        }))
      : [],
    approval_required: Boolean(result.approval_required || result.risk_level === 'high'),
  };
}

function sanitizeInboxResult(result) {
  return {
    summary: String(result.summary || ''),
    category: String(result.category || 'general'),
    priority: String(result.priority || 'medium'),
    due_date: result.due_date || null,
    action_items: Array.isArray(result.action_items) ? result.action_items.map(String) : [],
    detected_type: String(result.detected_type || 'unknown'),
    confidence: Number.isFinite(Number(result.confidence)) ? Number(result.confidence) : 0,
    recommended_save_mode: String(result.recommended_save_mode || 'inbox'),
    clarification_needed: Boolean(result.clarification_needed),
    clarification_question: result.clarification_question ? String(result.clarification_question) : '',
    missing_fields: Array.isArray(result.missing_fields) ? result.missing_fields.map(String) : [],
    parse_fallback: Boolean(result.parse_fallback),
  };
}

function sanitizeRuleDraftResult(result) {
  const riskLevel = String(result.risk_level || 'medium');
  const approvalRequired = Boolean(result.approval_required || riskLevel === 'high' || riskLevel === 'medium');

  return {
    rule_name: String(result.rule_name || ''),
    condition_text: String(result.condition_text || ''),
    category: String(result.category || 'general'),
    status: String(result.status || 'draft'),
    approval_required: approvalRequired,
    risk_level: riskLevel,
    rationale: result.rationale ? String(result.rationale) : '',
    actions: Array.isArray(result.actions)
      ? result.actions.map((action) => ({
          ...action,
          type: String(action?.type || 'noop'),
        }))
      : [],
    parse_fallback: Boolean(result.parse_fallback),
  };
}

function sanitizeBriefingResult(result) {
  return {
    headline: String(result.headline || '요약 정보 없음'),
    highlights: Array.isArray(result.highlights) ? result.highlights.map(String) : [],
    risks: Array.isArray(result.risks) ? result.risks.map(String) : [],
    next_actions: Array.isArray(result.next_actions) ? result.next_actions.map(String) : [],
    parse_fallback: Boolean(result.parse_fallback),
  };
}

function safeJsonParse(rawText) {
  if (typeof rawText !== 'string' || !rawText.trim()) {
    return null;
  }

  try {
    return JSON.parse(rawText);
  } catch (err) {
    const first = rawText.indexOf('{');
    const last = rawText.lastIndexOf('}');
    if (first !== -1 && last !== -1 && last > first) {
      try {
        return JSON.parse(rawText.slice(first, last + 1));
      } catch (extractErr) {
        return null;
      }
    }
    return null;
  }
}

function getCandidatesText(candidates) {
  const parts = candidates?.[0]?.content?.parts;
  if (!Array.isArray(parts)) {
    return '';
  }
  return parts
    .map((part) => part?.text)
    .filter(Boolean)
    .join('\n');
}

async function callGemini({ endpoint, promptKey, userPayload, defaultResult, sanitizeResult }) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    return {
      ok: false,
      status: 500,
      error: { code: 'MISSING_GEMINI_API_KEY', message: 'GEMINI_API_KEY is not configured.' },
    };
  }

  const promptProfile = await getPromptByKey(promptKey);
  if (!promptProfile) {
    return {
      ok: false,
      status: 500,
      error: { code: 'PROMPT_PROFILE_NOT_FOUND', message: `Prompt profile not found: ${promptKey}` },
    };
  }

  const globalPrompt = await getPromptByKey('global_system_prompt');
  const instruction = [globalPrompt?.content || '', promptProfile.content].filter(Boolean).join('\n\n');

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(GEMINI_MODEL)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const startedAt = Date.now();

  const body = {
    systemInstruction: {
      parts: [{ text: instruction }],
    },
    contents: [
      {
        role: 'user',
        parts: [{ text: JSON.stringify(userPayload) }],
      },
    ],
    generationConfig: {
      responseMimeType: 'application/json',
      temperature: 0.2,
    },
  };

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const raw = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    return {
      ok: false,
      status: resp.status,
      error: {
        code: 'GEMINI_API_ERROR',
        message: raw?.error?.message || 'Gemini API request failed.',
      },
    };
  }

  const text = getCandidatesText(raw.candidates);
  const parsed = safeJsonParse(text) || { ...defaultResult, parse_fallback: true };
  const safeResult = sanitizeResult(parsed);

  const latencyMs = Date.now() - startedAt;
  await logAiRun({
    endpoint,
    model: GEMINI_MODEL,
    prompt_key: promptKey,
    input_payload: userPayload,
    output_payload: safeResult,
    latency_ms: latencyMs,
  });

  return {
    ok: true,
    status: 200,
    data: {
      ok: true,
      endpoint,
      model: GEMINI_MODEL,
      prompt_key: promptKey,
      result: safeResult,
      latency_ms: latencyMs,
    },
  };
}

app.post('/api/ai/inbox-parse', async (req, res) => {
  if (!isObject(req.body)) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_BODY', message: 'JSON body object is required.' } });
  }

  const data = await callGemini({
    endpoint: '/api/ai/inbox-parse',
    promptKey: 'inbox_parse_prompt',
    userPayload: req.body,
    defaultResult: {
      summary: '',
      category: 'general',
      priority: 'medium',
      due_date: null,
      action_items: [],
      detected_type: 'unknown',
      confidence: 0,
      recommended_save_mode: 'inbox',
      clarification_needed: true,
      clarification_question: '내용을 조금 더 구체적으로 알려주세요.',
      missing_fields: ['unable_to_parse_json'],
    },
    sanitizeResult: sanitizeInboxResult,
  });

  return res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.post('/api/ai/analyze-item', async (req, res) => {
  if (!isObject(req.body)) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_BODY', message: 'JSON body object is required.' } });
  }

  const data = await callGemini({
    endpoint: '/api/ai/analyze-item',
    promptKey: 'item_analysis_prompt',
    userPayload: req.body,
    defaultResult: {
      summary: '',
      best_interpretation: '',
      confidence: 0,
      suggested_actions: [],
      approval_required: true,
    },
    sanitizeResult: sanitizeAnalyzeItemResult,
  });

  return res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.post('/api/ai/rule-draft', async (req, res) => {
  if (!isObject(req.body)) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_BODY', message: 'JSON body object is required.' } });
  }

  const data = await callGemini({
    endpoint: '/api/ai/rule-draft',
    promptKey: 'automation_rule_prompt',
    userPayload: req.body,
    defaultResult: {
      rule_name: '',
      condition_text: '',
      category: 'general',
      status: 'draft',
      approval_required: true,
      risk_level: 'medium',
      actions: [],
    },
    sanitizeResult: sanitizeRuleDraftResult,
  });

  return res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.post('/api/automation/rules', async (req, res) => {
  if (!isObject(req.body)) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_BODY', message: 'JSON body object is required.' } });
  }

  const payload = sanitizeRuleDraftResult(req.body);
  const safeStatus = payload.approval_required ? 'proposed' : payload.status || 'draft';
  const saved = await saveAutomationRule({
    ...payload,
    status: safeStatus,
    created_by: req.body.created_by || 'user',
  });

  return res.status(201).json({ ok: true, item: saved });
});

app.get('/api/ai/dashboard-briefing', async (req, res) => {
  const recentRuns = await all(
    `SELECT endpoint, model, latency_ms, created_at
     FROM ai_runs
     ORDER BY id DESC
     LIMIT 20`,
  );
  const rulesByStatus = await all(
    `SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS count
     FROM automation_rules
     GROUP BY COALESCE(status, 'unknown')`,
  );

  const data = await callGemini({
    endpoint: '/api/ai/dashboard-briefing',
    promptKey: 'dashboard_briefing_prompt',
    userPayload: {
      generated_at: new Date().toISOString(),
      ai_runs_recent: recentRuns,
      rules_by_status: rulesByStatus,
    },
    defaultResult: {
      headline: '대시보드 브리핑 생성 실패',
      highlights: [],
      risks: [],
      next_actions: [],
    },
    sanitizeResult: sanitizeBriefingResult,
  });

  return res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.get('/api/prompt-profiles', async (req, res) => {
  const items = await listPromptProfiles();
  return res.json({ ok: true, items });
});

app.put('/api/prompt-profiles/:promptKey', async (req, res) => {
  if (!isObject(req.body)) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_BODY', message: 'JSON body object is required.' } });
  }

  const promptKey = String(req.params.promptKey || '').trim();
  if (!promptKey) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_PROMPT_KEY', message: 'promptKey is required.' } });
  }

  if (typeof req.body.content !== 'string' || !req.body.content.trim()) {
    return res.status(400).json({ ok: false, error: { code: 'INVALID_CONTENT', message: 'content is required.' } });
  }

  const updated = await updatePromptProfile(promptKey, {
    title: typeof req.body.title === 'string' ? req.body.title : undefined,
    content: req.body.content,
  });

  if (!updated) {
    return res.status(404).json({ ok: false, error: { code: 'PROMPT_PROFILE_NOT_FOUND', message: 'Prompt profile not found.' } });
  }

  return res.json({ ok: true, item: updated });
});

app.use((err, req, res, next) => {
  if (err && err.type === 'entity.parse.failed') {
    res.status(400).json({
      ok: false,
      error: {
        code: 'INVALID_JSON_BODY',
        message: 'Request body must be valid JSON.',
      },
    });
    return;
  }
  next(err);
});

app.use((err, req, res, next) => {
  res.status(500).json({
    ok: false,
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: err?.message || 'Unexpected server error.',
    },
  });
});

(async () => {
  await initDb();
  app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
  });
})();
