import { useEffect } from 'react';
import { AppShellProvider, useAppShellContext } from './useAppShellContext';

function AppShellBootstrap({ children }: { children: React.ReactNode }) {
  const { loadPromptProfiles } = useAppShellContext();

  useEffect(() => {
    loadPromptProfiles().catch(() => {
      // Intentionally swallow bootstrap loading errors for now.
      // UI can render and offer explicit retry points.
    });
  }, [loadPromptProfiles]);

  return <>{children}</>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AppShellProvider>
      <AppShellBootstrap>{children}</AppShellBootstrap>
    </AppShellProvider>
  );
}
