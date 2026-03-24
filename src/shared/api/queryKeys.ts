export const queryKeys = {
  ai: {
    root: ['ai'] as const,
    dashboardBriefing: ['ai', 'dashboard-briefing'] as const,
    promptProfiles: ['ai', 'prompt-profiles'] as const,
    promptProfile: (promptKey: string) => ['ai', 'prompt-profiles', promptKey] as const,
  },
};
