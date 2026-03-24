import { useMemo, useState } from 'react';
import type { CSSProperties, KeyboardEventHandler } from 'react';
import type { AssistantSaveMode, InboxParseResult } from '@/shared/api/ai.types';
import { useAppShellContext } from '@/widgets/layout/ui/useAppShellContext';

const cardStyle: CSSProperties = {
  position: 'fixed',
  right: 20,
  bottom: 20,
  width: 340,
  padding: 14,
  border: '1px solid #ececec',
  borderRadius: 12,
  background: '#fff',
  boxShadow: '0 6px 18px rgba(0, 0, 0, 0.08)',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const buttonStyle: CSSProperties = {
  border: '1px solid #dddddd',
  background: '#fff',
  color: '#222',
  borderRadius: 8,
  padding: '7px 10px',
  fontSize: 12,
  cursor: 'pointer',
};

const infoRowStyle: CSSProperties = {
  fontSize: 12,
  color: '#333',
  lineHeight: 1.5,
};

function toKoreanType(type?: string) {
  if (type === 'event') return '일정';
  if (type === 'memo') return '메모';
  if (type === 'inbox') return '인박스';
  return '미확인';
}

function toKoreanMode(mode?: AssistantSaveMode) {
  if (mode === 'event') return '일정으로 저장';
  if (mode === 'memo') return '메모로 저장';
  return '인박스로 저장';
}

function confidenceText(confidence?: number) {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) {
    return '-';
  }
  return `${Math.round(confidence * 100)}%`;
}

export function FloatingAssistant() {
  const { runInboxParse, confirmAssistantSave, loading } = useAppShellContext();
  const [input, setInput] = useState('');
  const [parsed, setParsed] = useState<InboxParseResult | null>(null);
  const [statusText, setStatusText] = useState('');

  const isSendDisabled = useMemo(() => loading || !input.trim(), [input, loading]);

  const handleSend = async () => {
    const message = input.trim();
    if (!message) return;

    const response = await runInboxParse({ body: message });
    if (response.ok === false) {
      setStatusText(response.error.message || '분석에 실패했어요.');
      setParsed(null);
      return;
    }

    setParsed(response.result);
    setStatusText('분석 완료');
  };

  const handleSave = async (mode: AssistantSaveMode) => {
    const result = await confirmAssistantSave(mode, input.trim());
    setStatusText(result.message);
  };

  const onKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = async (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await handleSend();
    }
  };

  return (
    <section style={cardStyle} aria-label="플로팅 어시스턴트">
      <strong style={{ fontSize: 13, color: '#111' }}>어시스턴트</strong>

      <textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="메시지를 입력해 주세요"
        rows={4}
        style={{
          width: '100%',
          resize: 'none',
          border: '1px solid #e7e7e7',
          borderRadius: 10,
          padding: 10,
          fontSize: 13,
          outline: 'none',
        }}
      />

      <button type="button" onClick={handleSend} disabled={isSendDisabled} style={buttonStyle}>
        {loading ? '분석 중...' : '보내기'}
      </button>

      {parsed && (
        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8, display: 'grid', gap: 4 }}>
          <div style={infoRowStyle}>요약: {parsed.summary || '-'}</div>
          <div style={infoRowStyle}>유형: {toKoreanType(parsed.detected_type)}</div>
          <div style={infoRowStyle}>신뢰도: {confidenceText(parsed.confidence)}</div>
          <div style={infoRowStyle}>추천 저장: {toKoreanMode(parsed.recommended_save_mode)}</div>

          {parsed.clarification_needed && (
            <div style={{ ...infoRowStyle, color: '#b54708' }}>
              확인 필요: {parsed.clarification_question || '추가 정보가 필요합니다.'}
            </div>
          )}

          {!parsed.clarification_needed && parsed.recommended_save_mode && (
            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
              <button type="button" style={buttonStyle} onClick={() => handleSave('inbox')}>
                인박스로 저장
              </button>
              <button type="button" style={buttonStyle} onClick={() => handleSave('event')}>
                일정으로 저장
              </button>
              <button type="button" style={buttonStyle} onClick={() => handleSave('memo')}>
                메모로 저장
              </button>
            </div>
          )}
        </div>
      )}

      {statusText && <div style={{ fontSize: 12, color: '#666' }}>{statusText}</div>}
    </section>
  );
}
