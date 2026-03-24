import { requestJson } from './http';
import type {
  AiApiResponse,
  AnalyzeItemRequest,
  AnalyzeItemResult,
  DashboardBriefingResult,
  InboxParseRequest,
  InboxParseResult,
  PromptProfile,
  PromptProfilesResponse,
  RuleDraftRequest,
  RuleDraftResult,
  UpdatePromptProfileRequest,
  UpdatePromptProfileResponse,
} from './ai.types';

export function aiInboxParse(payload: InboxParseRequest) {
  return requestJson<AiApiResponse<InboxParseResult, '/api/ai/inbox-parse'>>('/api/ai/inbox-parse', {
    method: 'POST',
    body: payload,
  });
}

export function aiAnalyzeItem(payload: AnalyzeItemRequest) {
  return requestJson<AiApiResponse<AnalyzeItemResult, '/api/ai/analyze-item'>>('/api/ai/analyze-item', {
    method: 'POST',
    body: payload,
  });
}

export function aiRuleDraft(payload: RuleDraftRequest) {
  return requestJson<AiApiResponse<RuleDraftResult, '/api/ai/rule-draft'>>('/api/ai/rule-draft', {
    method: 'POST',
    body: payload,
  });
}

export function saveAutomationRule(payload: RuleDraftResult & { created_by?: string }) {
  return requestJson<{ ok: true; item: unknown }>('/api/automation/rules', {
    method: 'POST',
    body: payload,
  });
}

export function getDashboardBriefing() {
  return requestJson<AiApiResponse<DashboardBriefingResult, '/api/ai/dashboard-briefing'>>('/api/ai/dashboard-briefing');
}

export function getPromptProfiles() {
  return requestJson<PromptProfilesResponse>('/api/prompt-profiles');
}

export function getPromptProfileMap(items: PromptProfile[]): Record<string, PromptProfile> {
  return items.reduce<Record<string, PromptProfile>>((acc, item) => {
    acc[item.prompt_key] = item;
    return acc;
  }, {});
}

export function updatePromptProfile(promptKey: string, payload: UpdatePromptProfileRequest) {
  return requestJson<UpdatePromptProfileResponse>(`/api/prompt-profiles/${encodeURIComponent(promptKey)}`, {
    method: 'PUT',
    body: payload,
  });
}
