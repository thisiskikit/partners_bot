import { useMemo, useState } from 'react';
import { useAppShellContext } from '@/widgets/layout/ui/useAppShellContext';

export function PromptProfilesPage() {
  const { promptProfiles, loadPromptProfiles, savePromptProfile, loading } = useAppShellContext();
  const [selectedKey, setSelectedKey] = useState('');
  const [content, setContent] = useState('');
  const [statusText, setStatusText] = useState('');

  const keys = useMemo(() => Object.keys(promptProfiles), [promptProfiles]);
  const selected = selectedKey ? promptProfiles[selectedKey] : null;

  const handleLoad = async () => {
    await loadPromptProfiles();
    setStatusText('프롬프트 목록을 불러왔습니다.');
  };

  const handleSelect = (promptKey: string) => {
    setSelectedKey(promptKey);
    setContent(promptProfiles[promptKey]?.content || '');
  };

  const handleSave = async () => {
    if (!selectedKey || !content.trim()) return;
    await savePromptProfile(selectedKey, { content });
    setStatusText('프롬프트를 저장했습니다.');
  };

  return (
    <section style={{ border: '1px solid #ececec', borderRadius: 12, background: '#fff', padding: 12, display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <strong style={{ fontSize: 13 }}>프롬프트 프로필</strong>
        <button
          type="button"
          style={{ border: '1px solid #ddd', borderRadius: 8, background: '#fff', fontSize: 12, padding: '5px 8px' }}
          onClick={handleLoad}
          disabled={loading}
        >
          불러오기
        </button>
      </div>

      {keys.length === 0 && <div style={{ fontSize: 12, color: '#666' }}>불러온 프롬프트가 없습니다.</div>}

      {keys.length > 0 && (
        <select value={selectedKey} onChange={(event) => handleSelect(event.target.value)}>
          <option value="">프롬프트 선택</option>
          {keys.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </select>
      )}

      {selected && (
        <>
          <div style={{ fontSize: 12, color: '#444' }}>{selected.title}</div>
          <textarea
            value={content}
            rows={10}
            onChange={(event) => setContent(event.target.value)}
            style={{ width: '100%', border: '1px solid #ddd', borderRadius: 8, padding: 8, fontSize: 12 }}
          />
          <button
            type="button"
            style={{ border: '1px solid #ddd', borderRadius: 8, background: '#fff', fontSize: 12, padding: '6px 10px', width: 'fit-content' }}
            onClick={handleSave}
            disabled={loading || !content.trim()}
          >
            저장
          </button>
        </>
      )}

      {statusText && <div style={{ fontSize: 12, color: '#666' }}>{statusText}</div>}
    </section>
  );
}
