const express = require('express');
const { initDb, getPromptByKey, logAiRun, all } = require('./db');

const app = express();
const PORT = Number(process.env.PORT || 3000);
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';

app.use(express.json({ limit: '1mb' }));

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

async function callGemini({ endpoint, promptKey, userPayload, defaultResult }) {
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
        parts: [
          {
            text: JSON.stringify(userPayload),
          },
        ],
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
  const parsed = safeJsonParse(text) || {
    ...defaultResult,
    raw_text: text,
    parse_fallback: true,
  };

  const latencyMs = Date.now() - startedAt;
  await logAiRun({
    endpoint,
    model: GEMINI_MODEL,
    prompt_key: promptKey,
    input_payload: userPayload,
    output_payload: parsed,
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
      result: parsed,
      latency_ms: latencyMs,
    },
  };
}

app.post('/api/ai/inbox-parse', async (req, res) => {
  const payload = req.body && typeof req.body === 'object' ? req.body : {};
  const data = await callGemini({
    endpoint: '/api/ai/inbox-parse',
    promptKey: 'inbox_parse_prompt',
    userPayload: payload,
    defaultResult: {
      summary: '',
      category: 'general',
      priority: 'medium',
      due_date: null,
      action_items: [],
      missing_fields: ['unable_to_parse_json'],
    },
  });
  res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.post('/api/ai/analyze-item', async (req, res) => {
  const payload = req.body && typeof req.body === 'object' ? req.body : {};
  const data = await callGemini({
    endpoint: '/api/ai/analyze-item',
    promptKey: 'item_analysis_prompt',
    userPayload: payload,
    defaultResult: {
      diagnosis: '',
      risk_level: 'unknown',
      impact: 'unknown',
      recommendations: [],
      confidence: 0,
      parse_fallback: true,
    },
  });
  res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
});

app.post('/api/ai/rule-draft', async (req, res) => {
  const payload = req.body && typeof req.body === 'object' ? req.body : {};
  const data = await callGemini({
    endpoint: '/api/ai/rule-draft',
    promptKey: 'automation_rule_prompt',
    userPayload: payload,
    defaultResult: {
      rule_name: '',
      condition_text: '',
      category: 'general',
      status: 'draft',
      approval_required: true,
      actions: [],
      parse_fallback: true,
    },
  });
  res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
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
      parse_fallback: true,
    },
  });

  res.status(data.status).json(data.ok ? data.data : { ok: false, error: data.error });
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
