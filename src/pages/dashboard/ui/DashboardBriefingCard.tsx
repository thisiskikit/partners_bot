import { useEffect, useMemo, useState } from 'react';
import { useAppShellContext } from '@/widgets/layout/ui/useAppShellContext';

export function DashboardBriefingCard() {
  const { dashboardBriefing, refreshDashboardBriefing, loading } = useAppShellContext();
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    refreshDashboardBriefing().catch(() => {
      setStatusText('브리핑을 불러오지 못했습니다.');
    });
  }, [refreshDashboardBriefing]);

  const result = useMemo(() => {
    if (!dashboardBriefing || dashboardBriefing.ok === false) {
      return null;
    }
    return dashboardBriefing.result;
  }, [dashboardBriefing]);

  return (
    <section style={{ border: '1px solid #ececec', borderRadius: 12, background: '#fff', padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <strong style={{ fontSize: 13 }}>운영 브리핑</strong>
        <button
          type="button"
          style={{ border: '1px solid #ddd', borderRadius: 8, background: '#fff', fontSize: 12, padding: '5px 8px' }}
          onClick={() => refreshDashboardBriefing()}
          disabled={loading}
        >
          새로고침
        </button>
      </div>

      {!result && <div style={{ fontSize: 12, color: '#666' }}>브리핑을 불러오는 중입니다.</div>}
      {result && (
        <>
          <div style={{ fontSize: 12, marginBottom: 6 }}>{result.headline}</div>
          <div style={{ fontSize: 12, color: '#444' }}>핵심: {result.highlights.join(' / ') || '-'}</div>
          <div style={{ fontSize: 12, color: '#444' }}>리스크: {result.risks.join(' / ') || '-'}</div>
          <div style={{ fontSize: 12, color: '#444' }}>다음 행동: {result.next_actions.join(' / ') || '-'}</div>
        </>
      )}
      {statusText && <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>{statusText}</div>}
    </section>
  );
}
