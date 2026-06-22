import { toBlob } from 'html-to-image'

// React Flow のビューポート(.react-flow__viewport)を PNG Blob に変換する。
// fitView を呼んでから settleMs 待って撮るのは、ズーム/パンとレイアウトが落ち着いた状態を
// 撮るため(撮る前にビューをフィットさせないと、見えている範囲だけの中途半端な画像になる)。
// 初回(コールド)ロードはフォント/スタイルのインライン化が間に合わずに最初のフレームが
// 崩れることがあるので、自動エクスポート経路では settleMs を長めに渡すこと。
export async function captureCanvasBlob(fitView: () => void, settleMs = 150): Promise<Blob | null> {
  const flowElement = document.querySelector('.react-flow__viewport') as HTMLElement | null
  if (!flowElement) return null
  window.requestAnimationFrame(() => fitView())
  await new Promise((resolve) => setTimeout(resolve, settleMs))
  return toBlob(flowElement, { backgroundColor: '#fff' })
}

// Blob を object URL 経由でダウンロードさせる。クリップボード API に依存しないので、
// HTTP 接続や ClipboardItem 非対応ブラウザ、ヘッドレス/ディープリンクでも動く。
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// 重複しにくいダウンロードファイル名。ブラウザ実行なので Date を使ってよい。
export function imageFilename(): string {
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  return `dbt-lineage-${ts}.png`
}
