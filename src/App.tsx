import { useState } from 'react';
import { FloatingAssistant } from '@/features/assistant/ui/FloatingAssistant';
import { AutomationPage } from '@/pages/automation/ui/AutomationPage';
import { DashboardBriefingCard } from '@/pages/dashboard/ui/DashboardBriefingCard';
import { PromptProfilesPage } from '@/pages/settings/ui/PromptProfilesPage';
import { AppShell } from '@/widgets/layout/ui/AppShell';
import { RightPanel } from '@/widgets/layout/ui/RightPanel';

interface Item {
  id: string;
  title: string;
  content: string;
  category: string;
}

const initialItems: Item[] = [
  { id: 'item-1', title: '정산 요청 메일', content: '이번 주 금요일까지 세금계산서 처리 요청', category: 'ops' },
  { id: 'item-2', title: '파트너 CS', content: '배송 지연 관련 긴급 문의가 3건 접수됨', category: 'cs' },
];

export function App() {
  const [items, setItems] = useState<Item[]>(initialItems);
  const [selectedId, setSelectedId] = useState(items[0]?.id || '');
  const [memos, setMemos] = useState<string[]>([]);

  const selected = items.find((item) => item.id === selectedId) || null;

  return (
    <AppShell
      onCreateInboxItem={(payload) => {
        setMemos((prev) => [`인박스 저장: ${payload.summary}`, ...prev]);
      }}
      onCreateEvent={(payload) => {
        setMemos((prev) => [`일정 저장: ${payload.summary}`, ...prev]);
      }}
      onCreateMemo={(payload) => {
        setMemos((prev) => [`메모 저장: ${payload.summary}`, ...prev]);
      }}
      onAssignCategory={(itemId, category) => {
        setItems((prev) => prev.map((item) => (item.id === itemId ? { ...item, category } : item)));
      }}
    >
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: 20, display: 'grid', gap: 14 }}>
        <h1 style={{ fontSize: 20, margin: 0 }}>운영 허브 AI</h1>

        <section style={{ border: '1px solid #ececec', borderRadius: 12, background: '#fff', padding: 12 }}>
          <strong style={{ fontSize: 13 }}>작업 항목</strong>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: 8,
                  background: selectedId === item.id ? '#f7f7f7' : '#fff',
                  padding: '8px 10px',
                  fontSize: 12,
                }}
              >
                {item.title} ({item.category})
              </button>
            ))}
          </div>
        </section>

        <RightPanel
          selectedItem={selected}
          onCreateMemoDraft={(itemId, summary) => {
            setMemos((prev) => [`메모 초안(${itemId}): ${summary}`, ...prev]);
          }}
        />

        <DashboardBriefingCard />
        <AutomationPage />
        <PromptProfilesPage />

        <section style={{ border: '1px solid #ececec', borderRadius: 12, background: '#fff', padding: 12 }}>
          <strong style={{ fontSize: 13 }}>최근 저장 로그</strong>
          {memos.length === 0 && <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>아직 저장 로그가 없습니다.</div>}
          {memos.length > 0 && (
            <ul style={{ margin: '8px 0 0', paddingLeft: 16, fontSize: 12 }}>
              {memos.map((line, index) => (
                <li key={`${line}-${index}`}>{line}</li>
              ))}
            </ul>
          )}
        </section>
      </main>

      <FloatingAssistant />
    </AppShell>
  );
}
