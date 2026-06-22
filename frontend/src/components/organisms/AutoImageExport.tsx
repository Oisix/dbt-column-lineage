'use client'
import { useEffect, useRef } from 'react'
import { useReactFlow } from '@xyflow/react'
import { useSearchParams } from 'next/navigation'
import { useStore as useStoreZustand } from '@/store/zustand'
import { captureCanvasBlob, downloadBlob, imageFilename } from '@/lib/exportImage'

interface AutoImageExportProps {
  // レイアウトが一度完了して fitView が走ったか(Sidebar が setViewIsFit(true) する)。
  ready: boolean
  // 0 なら撮る対象がない(design が空/不正、fetch 失敗)ので発火させない。
  nodeCount: number
}

// URL に ?export=png があると、グラフ描画後に一度だけキャンバスを PNG として
// 自動ダウンロードする。?design=... 復元(API 非依存)と併用するヘッドレス用途が主。
// ReactFlowProvider の内側に置くこと(useReactFlow を使うため)。何も描画しない。
export const AutoImageExport = ({ ready, nodeCount }: AutoImageExportProps) => {
  const { fitView } = useReactFlow()
  const searchParams = useSearchParams()
  const setMessage = useStoreZustand((state) => state.setMessage)
  const exported = useRef(false)
  const format = searchParams.get('export')

  useEffect(() => {
    if (exported.current) return
    if (format !== 'png') return
    if (!ready || nodeCount === 0) return
    // ready は Sidebar が setViewIsFit(true) した瞬間に立つが、実際の fitView() は
    // そのあと requestAnimationFrame→setTimeout(0) で非同期に走る。さらにコールドロードでは
    // 最初のフレームが崩れやすい。なので Sidebar のタイミングに頼らず、ここで自前に
    // fitView→長めの settle→撮影する。1 回だけ実行する。
    exported.current = true
    ;(async () => {
      const blob = await captureCanvasBlob(fitView, 600)
      if (blob) {
        downloadBlob(blob, imageFilename())
        setMessage('Canvas image downloaded', 'success')
      } else {
        setMessage('Failed to export canvas image', 'error')
      }
      setTimeout(() => setMessage(null, null), 3000)
    })()
  }, [format, ready, nodeCount, fitView, setMessage])

  return null
}
