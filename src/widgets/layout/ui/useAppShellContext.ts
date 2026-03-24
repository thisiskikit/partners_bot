import { createContext, useCallback, useContext, useMemo, useState } from 'react';
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
  DashboardBriefingResult,
  InboxParseRequest,
  InboxParseResult,
  PromptProfile,
  RuleDraftRequest,
  RuleDraftResult,
  UpdatePromptProfileRequest,
} from '@/shared/api/ai.types';

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
}

const AppShellContext = createContext<AppShellContextValue | null>(null);

export function AppShellProvider({ children }: { children: React.ReactNode }) {
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
