import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  aiAnalyzeItem,
  aiInboxParse,
  aiRuleDraft,
  getDashboardBriefing,
  getPromptProfileMap,
  getPromptProfiles,
  updatePromptProfile,
} from '@/shared/api/ai';
import type {
  AiApiResponse,
  AnalyzeItemRequest,
  AnalyzeItemResult,
  AssistantSaveMode,
  DashboardBriefingResult,
  InboxParseRequest,
  InboxParseResult,
  PromptProfile,
  RuleDraftRequest,
  RuleDraftResult,
  UpdatePromptProfileRequest,
} from '@/shared/api/ai.types';

interface AssistantCreatePayload {
  summary: string;
  sourceText: string;
  parsed: InboxParseResult;
}

interface AppShellProviderProps {
  children: ReactNode;
  onCreateInboxItem?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onCreateEvent?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onCreateMemo?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onAssignCategory?: (itemId: string, category: string) => Promise<void> | void;
  onSaveAutomationRule?: (rule: RuleDraftResult) => Promise<void> | void;
}

export interface AppShellAiState {
  inboxParse: AiApiResponse<InboxParseResult, '/api/ai/inbox-parse'> | null;
  analyzeItem: AiApiResponse<AnalyzeItemResult, '/api/ai/analyze-item'> | null;
  ruleDraft: AiApiResponse<RuleDraftResult, '/api/ai/rule-draft'> | null;
  dashboardBriefing: AiApiResponse<DashboardBriefingResult, '/api/ai/dashboard-briefing'> | null;
  promptProfiles: Record<string, PromptProfile>;
  loading: boolean;
}

export interface AppShellContextValue extends AppShellAiState {
  loadPromptProfiles: () => Promise<void>;
  runInboxParse: (payload: InboxParseRequest) => Promise<AiApiResponse<InboxParseResult, '/api/ai/inbox-parse'>>;
  runAnalyzeItem: (payload: AnalyzeItemRequest) => Promise<AiApiResponse<AnalyzeItemResult, '/api/ai/analyze-item'>>;
  runRuleDraft: (payload: RuleDraftRequest) => Promise<AiApiResponse<RuleDraftResult, '/api/ai/rule-draft'>>;
  refreshDashboardBriefing: () => Promise<AiApiResponse<DashboardBriefingResult, '/api/ai/dashboard-briefing'>>;
  getItemActionPrompt: () => string;
  savePromptProfile: (promptKey: string, payload: UpdatePromptProfileRequest) => Promise<void>;
  confirmAssistantSave: (saveMode: AssistantSaveMode, sourceText: string) => Promise<{ ok: boolean; message: string }>;
  assignFinanceCategory: (itemId: string) => Promise<{ ok: boolean; message: string }>;
  approveRuleDraft: () => Promise<{ ok: boolean; message: string }>;
}

const AppShellContext = createContext<AppShellContextValue | null>(null);

function normalizeAnalyzeResult(result: AnalyzeItemResult): AnalyzeItemResult {
  if (result.best_interpretation && Array.isArray(result.suggested_actions)) {
    return result;
  }

  const confidence = typeof result.confidence === 'number' ? result.confidence : 0;
  const recommendations = Array.isArray(result.recommendations) ? result.recommendations : [];

  return {
    ...result,
    summary: result.summary || result.diagnosis || '',
    best_interpretation: result.best_interpretation || result.diagnosis || '해석 정보 없음',
    confidence,
    approval_required: result.approval_required ?? result.risk_level === 'high',
    suggested_actions:
      result.suggested_actions ||
      recommendations.map((label) => ({
        type: 'noop',
        label,
      })),
  };
}

export function AppShellProvider({
  children,
  onCreateInboxItem,
  onCreateEvent,
  onCreateMemo,
  onAssignCategory,
  onSaveAutomationRule,
}: AppShellProviderProps) {
  const [loading, setLoading] = useState(false);
  const [inboxParse, setInboxParse] = useState<AppShellContextValue['inboxParse']>(null);
  const [analyzeItem, setAnalyzeItem] = useState<AppShellContextValue['analyzeItem']>(null);
  const [ruleDraft, setRuleDraft] = useState<AppShellContextValue['ruleDraft']>(null);
  const [dashboardBriefing, setDashboardBriefing] = useState<AppShellContextValue['dashboardBriefing']>(null);
  const [promptProfiles, setPromptProfiles] = useState<Record<string, PromptProfile>>({});

  const withLoading = useCallback(async <T,>(fn: () => Promise<T>) => {
    setLoading(true);
    try {
      return await fn();
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPromptProfiles = useCallback(async () => {
    const payload = await withLoading(() => getPromptProfiles());
    setPromptProfiles(getPromptProfileMap(payload.items));
  }, [withLoading]);

  const runInboxParse = useCallback(async (payload: InboxParseRequest) => {
    const result = await withLoading(() => aiInboxParse(payload));
    setInboxParse(result);
    return result;
  }, [withLoading]);

  const runAnalyzeItem = useCallback(async (payload: AnalyzeItemRequest) => {
    const result = await withLoading(() => aiAnalyzeItem(payload));

    if (result.ok) {
      const normalized = {
        ...result,
        result: normalizeAnalyzeResult(result.result),
      };
      setAnalyzeItem(normalized);
      return normalized;
    }

    setAnalyzeItem(result);
    return result;
  }, [withLoading]);

  const runRuleDraft = useCallback(async (payload: RuleDraftRequest) => {
    const result = await withLoading(() => aiRuleDraft(payload));
    setRuleDraft(result);
    return result;
  }, [withLoading]);

  const refreshDashboardBriefing = useCallback(async () => {
    const result = await withLoading(() => getDashboardBriefing());
    setDashboardBriefing(result);
    return result;
  }, [withLoading]);

  const getItemActionPrompt = useCallback(() => {
    return (
      promptProfiles.item_analysis_prompt?.content ||
      promptProfiles.automation_rule_prompt?.content ||
      ''
    );
  }, [promptProfiles]);

  const savePromptProfile = useCallback(async (promptKey: string, payload: UpdatePromptProfileRequest) => {
    const updated = await withLoading(() => updatePromptProfile(promptKey, payload));
    setPromptProfiles((prev) => ({
      ...prev,
      [updated.item.prompt_key]: updated.item,
    }));
  }, [withLoading]);

  const confirmAssistantSave = useCallback(
    async (saveMode: AssistantSaveMode, sourceText: string) => {
      if (!inboxParse || inboxParse.ok !== true) {
        return { ok: false, message: '먼저 메시지를 분석해 주세요.' };
      }

      const payload: AssistantCreatePayload = {
        summary: inboxParse.result.summary,
        sourceText,
        parsed: inboxParse.result,
      };

      if (saveMode === 'inbox') {
        if (!onCreateInboxItem) {
          return { ok: false, message: '인박스 저장 기능이 연결되지 않았습니다.' };
        }
        await onCreateInboxItem(payload);
        return { ok: true, message: '인박스에 저장했어요.' };
      }

      if (saveMode === 'event') {
        if (!onCreateEvent) {
          return { ok: false, message: '일정 저장 기능이 연결되지 않았습니다.' };
        }
        await onCreateEvent(payload);
        return { ok: true, message: '일정으로 저장했어요.' };
      }

      if (!onCreateMemo) {
        return { ok: false, message: '메모 저장 기능이 연결되지 않았습니다.' };
      }
      await onCreateMemo(payload);
      return { ok: true, message: '메모로 저장했어요.' };
    },
    [inboxParse, onCreateEvent, onCreateInboxItem, onCreateMemo],
  );

  const assignFinanceCategory = useCallback(
    async (itemId: string) => {
      if (!onAssignCategory) {
        return { ok: false, message: '카테고리 변경 기능이 연결되지 않았습니다.' };
      }
      await onAssignCategory(itemId, 'finance');
      return { ok: true, message: '재무 카테고리로 지정했어요.' };
    },
    [onAssignCategory],
  );

  const approveRuleDraft = useCallback(async () => {
    if (!ruleDraft || ruleDraft.ok !== true) {
      return { ok: false, message: '저장할 룰 초안이 없습니다.' };
    }

    if (!onSaveAutomationRule) {
      return { ok: false, message: '룰 저장 기능이 연결되지 않았습니다.' };
    }

    const safeStatus = ruleDraft.result.approval_required ? 'proposed' : 'draft';
    await onSaveAutomationRule({
      ...ruleDraft.result,
      status: safeStatus,
    });
    return {
      ok: true,
      message: safeStatus === 'proposed' ? '승인 대기 상태로 저장했어요.' : '룰 초안을 저장했어요.',
    };
  }, [onSaveAutomationRule, ruleDraft]);

  const value = useMemo<AppShellContextValue>(
    () => ({
      inboxParse,
      analyzeItem,
      ruleDraft,
      dashboardBriefing,
      promptProfiles,
      loading,
      loadPromptProfiles,
      runInboxParse,
      runAnalyzeItem,
      runRuleDraft,
      refreshDashboardBriefing,
      getItemActionPrompt,
      savePromptProfile,
      confirmAssistantSave,
      assignFinanceCategory,
      approveRuleDraft,
    }),
    [
      inboxParse,
      analyzeItem,
      ruleDraft,
      dashboardBriefing,
      promptProfiles,
      loading,
      loadPromptProfiles,
      runInboxParse,
      runAnalyzeItem,
      runRuleDraft,
      refreshDashboardBriefing,
      getItemActionPrompt,
      savePromptProfile,
      confirmAssistantSave,
      assignFinanceCategory,
      approveRuleDraft,
    ],
  );

  return <AppShellContext.Provider value={value}>{children}</AppShellContext.Provider>;
}

export function useAppShellContext() {
  const context = useContext(AppShellContext);
  if (!context) {
    throw new Error('useAppShellContext must be used within AppShellProvider.');
  }
  return context;
}
