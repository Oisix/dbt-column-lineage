'use client'
import React, { createContext, useContext, useEffect, useState } from 'react'

export interface Brand {
  name?: string
  logoUrl?: string
  faviconUrl?: string
  primaryColor?: string
  fontUrl?: string
  fontFamily?: string
}

const BrandContext = createContext<Brand>({})
export const useBrand = () => useContext(BrandContext)

export const DEFAULT_APP_NAME = 'dbt column lineage'

// '#rgb' / '#rrggbb' -> 'r,g,b'(Select の rgba(var(--primary), …) が使う形式)
const hexToRgbTriplet = (hex: string): string => {
  const h = hex.length === 4 ? [...hex.slice(1)].map((c) => c + c).join('') : hex.slice(1)
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(',')
}

// バックエンドの BRAND_* (/api/v1/branding) を実行時に取得して CSS 変数・フォント・ファビコン・タイトルへ反映する。
// 取得に失敗しても既定の見た目のまま動く(ブランド設定は任意)。
export const BrandProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [brand, setBrand] = useState<Brand>({})

  useEffect(() => {
    const hostName = process.env.NEXT_PUBLIC_API_HOSTNAME || ''
    fetch(`${hostName}/api/v1/branding`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((b: Brand) => {
        const root = document.documentElement
        if (b.primaryColor) {
          root.style.setProperty('--brand', b.primaryColor)
          root.style.setProperty('--primary', hexToRgbTriplet(b.primaryColor))
          // ノード種別色はブランド色の濃淡(判別できるよう強さを変える)
          const tint = (pct: number) => `color-mix(in srgb, ${b.primaryColor} ${pct}%, white)`
          Object.entries({ table: 12, view: 6, incremental: 38, snapshot: 24, seed: 18 }).forEach(([type, pct]) =>
            root.style.setProperty(`--node-${type}`, tint(pct)))
        }
        if (b.fontUrl) {
          const link = document.createElement('link')
          link.rel = 'stylesheet'
          link.href = b.fontUrl
          document.head.appendChild(link)
        }
        if (b.fontFamily) {
          document.body.style.fontFamily = b.fontFamily
        }
        if (b.faviconUrl) {
          document.querySelectorAll("link[rel~='icon']").forEach((el) => el.remove())
          const icon = document.createElement('link')
          icon.rel = 'icon'
          icon.href = b.faviconUrl
          document.head.appendChild(icon)
        }
        if (b.name) {
          // Next が hydration 後に metadata の title を書き戻すので、変わるたびにブランド名へ戻す
          const name = b.name
          const applyTitle = () => { if (document.title !== name) document.title = name }
          applyTitle()
          new MutationObserver(applyTitle).observe(document.head, { subtree: true, childList: true, characterData: true })
        }
        setBrand(b)
      })
      .catch(() => {})
  }, [])

  return <BrandContext.Provider value={brand}>{children}</BrandContext.Provider>
}
