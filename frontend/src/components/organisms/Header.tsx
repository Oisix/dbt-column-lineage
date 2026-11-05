'use client'
import React, { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { SearchDialog } from '@/components/ui/SearchDialog'
import ThemePicker from '@/components/ui/ThemePicker'
import { useStore as useStoreZustand } from '@/store/zustand'
import { AlertTriangle, Check, Info, Loader, Search } from 'lucide-react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { DEFAULT_APP_NAME, useBrand } from '@/components/organisms/BrandProvider'

export interface HeaderProps {
  handleFetchData: Function
}

export interface DashboardOption {
  label: string
  value: string
  description: string
}

export const Header: React.FC<HeaderProps> = ({ handleFetchData }) => {
  const [lineageMode, setLineageMode] = useState('/cl')

  const brand = useBrand()
  const pathname = usePathname()
  const router = useRouter()

  const triggerSubmitClicked = useStoreZustand((state) => state.triggerSubmitClicked)
  const loading = useStoreZustand((state) => state.loading)
  const message = useStoreZustand((state) => state.message)
  const messageType = useStoreZustand((state) => state.messageType)
  const isSubmitDisabled = useStoreZustand((state) => state.isSubmitDisabled)

  const getMessageIcon = (type: string | null) => {
    switch (type) {
      case 'success':
        return <Check className="inline-block mr-2" size={20} />
      case 'error':
        return <AlertTriangle className="inline-block mr-2" size={20} />
      default:
        return <Info className="inline-block mr-2" size={20} />
    }
  }

  // マウント時に現在の pathname で lineageMode を初期化する(以降は select の onChange で遷移)。
  /* eslint-disable react-hooks/exhaustive-deps, react-hooks/set-state-in-effect */
  useEffect(() => {
    if (pathname !== lineageMode) {
      setLineageMode(pathname)
    }
  }, [])
  /* eslint-enable react-hooks/exhaustive-deps, react-hooks/set-state-in-effect */

  return (
    <div>
      {message && (
        <div
          className={`absolute top-4 right-4 px-4 py-3 rounded shadow-md z-50 flex items-center ${
            messageType === 'success' ? 'bg-green-100 border-green-400 text-green-700' :
              messageType === 'error' ? 'bg-red-100 border-red-400 text-red-700' :
                'bg-blue-100 border-blue-400 text-blue-700'
          }`}
          role="alert"
        >
          {getMessageIcon(messageType)}
          <div className="markdown sm:inline text-xs max-w-xl">
            <Markdown remarkPlugins={[remarkGfm]}>{message}</Markdown>
          </div>
        </div>
      )}
      <header className="relative z-30 bg-white border-b shadow-xs">
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
          <div className="flex items-center gap-3">
            {brand.logoUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={brand.logoUrl} alt={brand.name || DEFAULT_APP_NAME} className="h-7 w-auto" />
            )}
            {!brand.logoUrl && (
              <span className="text-base font-semibold tracking-tight text-gray-900">
                {brand.name || DEFAULT_APP_NAME}
              </span>
            )}
          </div>

          <select
            value={lineageMode}
            onChange={e => router.push(e.target.value)}
            className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-hidden focus:ring-2 focus:ring-brand"
          >
            <option value="/cte">CTE Lineage</option>
            <option value="/cl">Column Level Lineage</option>
          </select>

          <div className="flex flex-1 flex-wrap items-center gap-2 md:border-l md:border-gray-200 md:pl-4">
            <SearchDialog
              handleFetchData={handleFetchData}
            />
            <button
              type="button"
              className="rounded-lg px-4 py-2 text-sm font-medium bg-brand text-white flex items-center shadow-sm hover:bg-brand-hover transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={triggerSubmitClicked}
              disabled={isSubmitDisabled}
            >
              {loading ? (
                <Loader className="animate-spin mr-2" size={16} />
              ) : (
                <Search className="mr-2" size={16} />
              )}
              <span>{loading ? 'Loading...' : 'Search'}</span>
            </button>
          </div>
          <div className="ml-auto">
            <ThemePicker />
          </div>
        </nav>
      </header>
    </div>
  )
}