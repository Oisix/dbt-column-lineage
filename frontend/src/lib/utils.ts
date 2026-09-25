export const getColorClassForMaterialized = (type: string): string => {
  switch (type) {
    case 'table':
      return 'bg-[#E6E6FA]'
    case 'view':
      return 'bg-[#F0E6FF]'
    case 'incremental':
      return 'bg-[#ADD8E6]'
    case 'snapshot':
      return 'bg-indigo-200'
    case 'seed':
      return 'bg-violet-200'
    default:
      return 'bg-gray-200'
  }
}

export const materializedTypes = [
  'table',
  'view',
  'incremental',
  'snapshot',
  'seed',
  // Add any other types here
]
// 設計ノード(editableTableNode)の変更区分。PR のリネージ図で「今回新規 / 今回変更 / 触っていない既存」を
// 見分けるために使う。未指定のノードは従来どおりの見た目(紫破線)のまま。
export type DesignChangeType = 'new' | 'modified' | 'existing'

export const designChangeTypes: DesignChangeType[] = ['new', 'modified', 'existing']

// 外枠(border)とバッジ。existing は解析済みの実テーブルノードと同じ灰色の実線にし、
// 「紫=設計(これから作る/変える)」の色言語を崩さない。modified は琥珀色の破線。
export const designChangeStyles: Record<DesignChangeType, { border: string; badge: string | null; label: string }> = {
  new: { border: 'border-2 border-dashed border-violet-500', badge: 'bg-violet-600 text-white', label: 'NEW' },
  modified: { border: 'border-2 border-dashed border-amber-500', badge: 'bg-amber-500 text-white', label: 'MODIFIED' },
  existing: { border: 'border-2 border-solid border-gray-300', badge: null, label: 'EXISTING' },
}

export const isDesignChangeType = (v: unknown): v is DesignChangeType =>
  typeof v === 'string' && (designChangeTypes as string[]).includes(v)
