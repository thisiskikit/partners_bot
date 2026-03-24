import { useEffect, useMemo, useState } from 'react';
import { AiSuggestionsCard } from '@/features/assistant/ui/AiSuggestionsCard';
import { useAppShellContext } from './useAppShellContext';

interface SelectedItem {
  id: string;
  title?: string;
  content?: string;
}

interface RightPanelProps {
  selectedItem: SelectedItem | null;
  onCreateMemoDraft?: (itemId: string, summary: string) => void;
}

export function RightPanel({ selectedItem, onCreateMemoDraft }: RightPanelProps) {
  const { runAnalyzeItem, analyzeItem, assignFinanceCategory, loading } = useAppShellContext();
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    if (!selectedItem) return;

    runAnalyzeItem({
      item_title: selectedItem.title,
      details: selectedItem.content,
      item_id: selectedItem.id,
    }).catch(() => {
      setStatusText('AI 분석을 불러오지 못했습니다.');
    });
  }, [runAnalyzeItem, selectedItem]);

  const result = useMemo(() => {
    if (!analyzeItem || analyzeItem.ok === false) {
      return null;
    }
    return analyzeItem.result;
  }, [analyzeItem]);

  const handleAssignFinance = async () => {
    if (!selectedItem) return;
    const resultMessage = await assignFinanceCategory(selectedItem.id);
    setStatusText(resultMessage.message);
  };

  const handleMemoDraft = () => {
    if (!selectedItem || !result) return;
    onCreateMemoDraft?.(selectedItem.id, result.summary || 'AI 메모 초안');
    setStatusText('메모 초안으로 넘겼어요.');
  };

  const handleNoop = () => {
    setStatusText('변경 없이 보류했습니다.');
  };

  if (!selectedItem) {
    return <aside style={{ padding: 12, fontSize: 12, color: '#666' }}>선택된 항목이 없습니다.</aside>;
  }

  if (!result) {
    return <aside style={{ padding: 12, fontSize: 12, color: '#666' }}>AI 제안을 불러오는 중입니다.</aside>;
  }

  return (
    <aside>
      <AiSuggestionsCard
        result={result}
        loading={loading}
        onAssignFinance={handleAssignFinance}
        onMemoDraft={handleMemoDraft}
        onNoop={handleNoop}
        statusText={statusText}
      />
    </aside>
  );
}
