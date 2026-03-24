export type AiEndpoint =
  | '/api/ai/inbox-parse'
  | '/api/ai/analyze-item'
  | '/api/ai/rule-draft'
  | '/api/ai/dashboard-briefing';

export interface ApiErrorShape {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  ok: false;
  error: ApiErrorShape;
}

export interface AiSuccessEnvelope<T, P extends string = string> {
  ok: true;
  endpoint: P;
  model: string;
  prompt_key: string;
  result: T;
  latency_ms: number;
}

export type AiApiResponse<T, P extends string = string> = AiSuccessEnvelope<T, P> | ApiErrorResponse;

export interface InboxParseRequest {
  subject?: string;
  body?: string;
  sender?: string;
  [key: string]: unknown;
}

export type AssistantSaveMode = 'inbox' | 'event' | 'memo';

export interface InboxParseResult {
  summary: string;
  category: string;
  priority: 'low' | 'medium' | 'high' | string;
  due_date: string | null;
  action_items: string[];
  detected_type?: 'inbox' | 'event' | 'memo' | 'unknown' | string;
  confidence?: number;
  recommended_save_mode?: AssistantSaveMode;
  clarification_needed?: boolean;
  clarification_question?: string;
  missing_fields?: string[];
  raw_text?: string;
  parse_fallback?: boolean;
}

export interface AnalyzeItemRequest {
  item_title?: string;
  details?: string;
  [key: string]: unknown;
}

export interface AnalyzeItemResult {
  diagnosis: string;
  risk_level: 'low' | 'medium' | 'high' | 'unknown' | string;
  impact: string;
  recommendations: string[];
  confidence: number;
  raw_text?: string;
  parse_fallback?: boolean;
}

export interface RuleDraftRequest {
  policy_context?: string;
  examples?: string[];
  [key: string]: unknown;
}

export interface RuleDraftAction {
  type: string;
  [key: string]: unknown;
}

export interface RuleDraftResult {
  rule_name: string;
  condition_text: string;
  category: string;
  status: 'draft' | 'proposed' | string;
  approval_required: boolean;
  actions: RuleDraftAction[];
  raw_text?: string;
  parse_fallback?: boolean;
}

export interface DashboardBriefingResult {
  headline: string;
  highlights: string[];
  risks: string[];
  next_actions: string[];
  raw_text?: string;
  parse_fallback?: boolean;
}

export interface PromptProfile {
  id: number;
  prompt_key: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface PromptProfilesResponse {
  ok: true;
  items: PromptProfile[];
}

export interface UpdatePromptProfileRequest {
  title?: string;
  content: string;
}

export interface UpdatePromptProfileResponse {
  ok: true;
  item: PromptProfile;
}
