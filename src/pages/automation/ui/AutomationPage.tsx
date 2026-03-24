import { useState } from 'react';
import type { CSSProperties } from 'react';
import { useAppShellContext } from '@/widgets/layout/ui/useAppShellContext';

const boxStyle: CSSProperties = {
  border: '1px solid #ececec',
  borderRadius: 12,
  background: '#fff',
  padding: 14,
};

const buttonStyle: CSSProperties = {
  border: '1px solid #dddddd',
  borderRadius: 8,
  background: '#fff',
  fontSize: 12,
  padding: '8px 10px',
  cursor: 'pointer',
};

export function AutomationPage() {
  const { runRuleDraft, ruleDraft, approveRuleDraft, loading } = useAppShellContext();
  const [promptInput, setPromptInput] = useState('');
  const [statusText, setStatusText] = useState('');

  const handleDraft = async () => {
    const text = promptInput.trim();
    if (!text) return;

    const response = await runRuleDraft({ policy_context: text });
    if (response.ok === false) {
      setStatusText(response.error.message || '룰 초안 생성에 실패했습니다.');
      return;
    }
    setStatusText('룰 초안을 생성했습니다.');
  };

  const handleApproveAndSave = async () => {
    const result = await approveRuleDraft();
    setStatusText(result.message);
  };

  return (
    <section style={{ display: 'grid', gap: 12 }}>
      <div style={boxStyle}>
        <strong style={{ fontSize: 14 }}>자동화 룰 초안</strong>
        <p style={{ fontSize: 12, color: '#666', marginTop: 6 }}>운영 문장을 입력하면 AI가 룰 초안을 제안합니다.</p>
        <textarea
          value={promptInput}
          onChange={(event) => setPromptInput(event.target.value)}
          placeholder="예: 긴급 문의가 들어오면 운영 채널에 즉시 알림"
          rows={4}
          style={{
            width: '100%',
            border: '1px solid #e6e6e6',
            borderRadius: 10,
            padding: 10,
            fontSize: 13,
            resize: 'vertical',
          }}
        />
        <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
          <button type="button" style={buttonStyle} disabled={loading || !promptInput.trim()} onClick={handleDraft}>
            {loading ? '생성 중...' : '룰 초안 생성'}
          </button>
          <button type="button" style={buttonStyle} disabled={loading || !ruleDraft || ruleDraft.ok === false} onClick={handleApproveAndSave}>
            승인/저장
          </button>
        </div>
      </div>

      {ruleDraft && ruleDraft.ok && (
        <div style={boxStyle}>
          <strong style={{ fontSize: 13 }}>AI 초안 결과</strong>
          <div style={{ fontSize: 12, marginTop: 8 }}>이름: {ruleDraft.result.rule_name}</div>
          <div style={{ fontSize: 12 }}>조건: {ruleDraft.result.condition_text}</div>
          <div style={{ fontSize: 12 }}>카테고리: {ruleDraft.result.category}</div>
          <div style={{ fontSize: 12 }}>위험도: {ruleDraft.result.risk_level || '-'}</div>
          <div style={{ fontSize: 12 }}>승인 필요: {ruleDraft.result.approval_required ? '필요' : '불필요'}</div>
          <div style={{ fontSize: 12 }}>저장 상태: {ruleDraft.result.approval_required ? 'proposed(승인대기)' : 'draft'}</div>
          <div style={{ fontSize: 12, marginTop: 6 }}>액션: {ruleDraft.result.actions?.map((item) => item.type).join(', ') || '-'}</div>
        </div>
      )}

      {statusText && <div style={{ fontSize: 12, color: '#666' }}>{statusText}</div>}
    </section>
  );
}
