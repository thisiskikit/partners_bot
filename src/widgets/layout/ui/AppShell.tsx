import { useEffect } from 'react';
import type { ReactNode } from 'react';
import type { RuleDraftResult } from '@/shared/api/ai.types';
import { AppShellProvider, useAppShellContext } from './useAppShellContext';

interface AssistantCreatePayload {
  summary: string;
  sourceText: string;
  parsed: {
    category: string;
    priority: string;
    due_date: string | null;
    action_items: string[];
    detected_type?: string;
    confidence?: number;
    recommended_save_mode?: 'inbox' | 'event' | 'memo';
    clarification_needed?: boolean;
    clarification_question?: string;
  };
}

interface AppShellProps {
  children: ReactNode;
  onCreateInboxItem?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onCreateEvent?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onCreateMemo?: (payload: AssistantCreatePayload) => Promise<void> | void;
  onAssignCategory?: (itemId: string, category: string) => Promise<void> | void;
  onSaveAutomationRule?: (rule: RuleDraftResult) => Promise<void> | void;
}

function AppShellBootstrap({ children }: { children: ReactNode }) {
  const { loadPromptProfiles } = useAppShellContext();

  useEffect(() => {
    loadPromptProfiles().catch(() => {
      // Intentionally swallow bootstrap loading errors for now.
      // UI can render and offer explicit retry points.
    });
  }, [loadPromptProfiles]);

  return <>{children}</>;
}

export function AppShell({
  children,
  onCreateInboxItem,
  onCreateEvent,
  onCreateMemo,
  onAssignCategory,
  onSaveAutomationRule,
}: AppShellProps) {
  return (
    <AppShellProvider
      onCreateInboxItem={onCreateInboxItem}
      onCreateEvent={onCreateEvent}
      onCreateMemo={onCreateMemo}
      onAssignCategory={onAssignCategory}
      onSaveAutomationRule={onSaveAutomationRule}
    >
      <AppShellBootstrap>{children}</AppShellBootstrap>
    </AppShellProvider>
  );
}
