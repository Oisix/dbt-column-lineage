'use client'
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'

export interface Brand {
  name?: string
  logoUrl?: string
  faviconUrl?: string
  primaryColor?: string
  fontUrl?: string
  fontFamily?: string
}

interface ThemeColor {
  color: string | null // 利用者が選んだ色(未選択なら null = サーバー設定/既定色)
  setColor: (color: string | null) => void
}

const BrandContext = createContext<Brand>({})
const ThemeColorContext = createContext<ThemeColor>({ color: null, setColor: () => {} })
export const useBrand = () => useContext(BrandContext)
export const useThemeColor = () => useContext(ThemeColorContext)

export const DEFAULT_APP_NAME = 'dbt column lineage'
export const DEFAULT_PRIMARY_COLOR = '#007bf5'
const STORAGE_KEY = 'dbt-column-lineage:theme-color'
const HEX = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

// '#rgb' / '#rrggbb' -> 'r,g,b'(Select の rgba(var(--primary), …) が使う形式)
const hexToRgbTriplet = (hex: string): string => {
  const h = hex.length === 4 ? [...hex.slice(1)].map((c) => c + c).join('') : hex.slice(1)
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(',')
}

const NODE_TINTS = { table: 12, view: 6, incremental: 38, snapshot: 24, seed: 18 }
const THEME_VARS = ['--brand', '--primary', ...Object.keys(NODE_TINTS).map((t) => `--node-${t}`)]

// 色を CSS 変数へ反映する。null なら global.css の既定値に戻す。
const applyPrimaryColor = (color: string | null) => {
  const root = document.documentElement
  if (!color) {
    THEME_VARS.forEach((v) => root.style.removeProperty(v))
    return
  }
  root.style.setProperty('--brand', color)
  root.style.setProperty('--primary', hexToRgbTriplet(color))
  // ノード種別色はブランド色の濃淡(判別できるよう強さを変える)
  Object.entries(NODE_TINTS).forEach(([type, pct]) =>
    root.style.setProperty(`--node-${type}`, `color-mix(in srgb, ${color} ${pct}%, white)`))
}

// ブランド設定(/api/v1/branding)を実行時に取得して反映し、利用者が選んだテーマ色を localStorage に覚える。
// 優先順位: 利用者が選んだ色 > サーバーのブランド色 > 既定色。取得失敗や localStorage 不可でも既定の見た目で動く。
export const BrandProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [brand, setBrand] = useState<Brand>({})
  const [userColor, setUserColor] = useState<string | null>(null)

  // マウント時に保存済みのテーマ色を読む(SSG のため初期描画では読めない)
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved && HEX.test(saved)) setUserColor(saved)
    } catch {}
  }, [])
  /* eslint-enable react-hooks/set-state-in-effect */

  const setColor = useCallback((color: string | null) => {
    setUserColor(color)
    try {
      if (color) localStorage.setItem(STORAGE_KEY, color)
      else localStorage.removeItem(STORAGE_KEY)
    } catch {}
  }, [])

  useEffect(() => {
    applyPrimaryColor(userColor ?? brand.primaryColor ?? null)
  }, [userColor, brand.primaryColor])

  useEffect(() => {
    const hostName = process.env.NEXT_PUBLIC_API_HOSTNAME || ''
    fetch(`${hostName}/api/v1/branding`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((b: Brand) => {
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

  return (
    <BrandContext.Provider value={brand}>
      <ThemeColorContext.Provider value={{ color: userColor, setColor }}>{children}</ThemeColorContext.Provider>
    </BrandContext.Provider>
  )
}
