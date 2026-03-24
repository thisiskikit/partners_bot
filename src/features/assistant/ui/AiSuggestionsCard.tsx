import type { CSSProperties } from 'react';
import type { AnalyzeItemResult } from '@/shared/api/ai.types';

interface AiSuggestionsCardProps {
  result: AnalyzeItemResult;
  loading?: boolean;
  onAssignFinance: () => Promise<void>;
  onMemoDraft: () => void;
  onNoop: () => void;
  statusText?: string;
}

const panelStyle: CSSProperties = {
  border: '1px solid #eeeeee',
  borderRadius: 12,
  background: '#fff',
  padding: 12,
  display: 'grid',
  gap: 6,
};

const actionButton: CSSProperties = {
  border: '1px solid #dddddd',
  borderRadius: 8,
  background: '#fff',
  fontSize: 12,
  padding: '7px 10px',
  cursor: 'pointer',
};

export function AiSuggestionsCard({
  result,
  loading,
  onAssignFinance,
  onMemoDraft,
  onNoop,
  statusText,
}: AiSuggestionsCardProps) {
  return (
    <section style={panelStyle} aria-label="AI 제안 카드">
      <strong style={{ fontSize: 13 }}>AI 제안</strong>
      <div style={{ fontSize: 12 }}>요약: {result.summary || '-'}</div>
      <div style={{ fontSize: 12 }}>해석: {result.best_interpretation || '-'}</div>
      <div style={{ fontSize: 12 }}>신뢰도: {typeof result.confidence === 'number' ? `${Math.round(result.confidence * 100)}%` : '-'}</div>
      <div style={{ fontSize: 12 }}>승인 필요: {result.approval_required ? '필요' : '불필요'}</div>

      <div style={{ marginTop: 4 }}>
        <div style={{ fontSize: 12, marginBottom: 4 }}>추천 액션</div>
        {result.suggested_actions?.length ? (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: '#444' }}>
            {result.suggested_actions.map((action, index) => (
              <li key={`${action.type}-${index}`}>{action.label}</li>
            ))}
          </ul>
        ) : (
          <div style={{ fontSize: 12, color: '#777' }}>추천 액션이 없습니다.</div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
        <button type="button" style={actionButton} disabled={loading} onClick={onAssignFinance}>
          재무로 분류
        </button>
        <button type="button" style={actionButton} onClick={onMemoDraft}>
          메모 초안
        </button>
        <button type="button" style={actionButton} onClick={onNoop}>
          보류
        </button>
      </div>

      {statusText && <div style={{ fontSize: 12, color: '#666' }}>{statusText}</div>}
    </section>
  );
}
