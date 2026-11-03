'use client'
import React, { useState } from 'react'
import { Check, Palette, RotateCcw } from 'lucide-react'
import { DEFAULT_PRIMARY_COLOR, useBrand, useThemeColor } from '@/components/organisms/BrandProvider'

const PRESETS = [
  { name: 'Blue', color: '#007bf5' },
  { name: 'Indigo', color: '#4f46e5' },
  { name: 'Violet', color: '#7c3aed' },
  { name: 'Rose', color: '#e11d48' },
  { name: 'Orange', color: '#ea580c' },
  { name: 'Green', color: '#16a34a' },
  { name: 'Teal', color: '#0f766e' },
  { name: 'Slate', color: '#334155' },
]

// テーマ色の選択(プリセット + 任意色)。選択は利用者のブラウザに保存され、サーバーのブランド色より優先される。
const ThemePicker: React.FC = () => {
  const [open, setOpen] = useState(false)
  const brand = useBrand()
  const { color, setColor } = useThemeColor()
  const current = (color ?? brand.primaryColor ?? DEFAULT_PRIMARY_COLOR).toLowerCase()

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-2.5 py-2 text-sm text-gray-700 hover:bg-gray-50"
        title="Theme colour"
        aria-expanded={open}
      >
        <Palette size={16} />
        <span className="h-3.5 w-3.5 rounded-full border border-black/10" style={{ backgroundColor: current }} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-60 rounded-xl border border-gray-200 bg-white p-3 shadow-lg">
            <p className="mb-2 text-xs font-semibold text-gray-500">Theme colour</p>
            <div className="grid grid-cols-4 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.color}
                  type="button"
                  title={p.name}
                  onClick={() => setColor(p.color)}
                  className="flex h-9 items-center justify-center rounded-lg text-white shadow-xs hover:scale-105 transition-transform"
                  style={{ backgroundColor: p.color }}
                >
                  {current === p.color && <Check size={16} />}
                </button>
              ))}
            </div>
            <label className="mt-3 flex items-center justify-between text-xs text-gray-600">
              Custom
              <input
                type="color"
                value={/^#[0-9a-f]{6}$/.test(current) ? current : DEFAULT_PRIMARY_COLOR}
                onChange={(e) => setColor(e.target.value)}
                className="h-7 w-12 cursor-pointer rounded-sm border border-gray-200 bg-white p-0.5"
              />
            </label>
            {color && (
              <button
                type="button"
                onClick={() => setColor(null)}
                className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-200 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
              >
                <RotateCcw size={12} /> Reset to default
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default ThemePicker
