'use client'
import {FcGoogle} from 'react-icons/fc'
import {DEFAULT_APP_NAME, useBrand} from '@/components/organisms/BrandProvider'

export default function Login() {
  const brand = useBrand()
  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-brand-soft px-4">
      <div className="w-full max-w-sm rounded-2xl border bg-white p-8 shadow-sm text-center">
        {brand.logoUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={brand.logoUrl} alt={brand.name || DEFAULT_APP_NAME} className="mx-auto mb-4 h-10 w-auto" />
        )}
        {!brand.logoUrl && (
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
            {brand.name || DEFAULT_APP_NAME}
          </h1>
        )}
        <p className="mt-2 text-sm text-gray-500">
          Sign in to visualize your column-level lineage
        </p>

        <a href="/oauth" className="mt-8 block">
          <button
            type="button"
            className="w-full flex items-center justify-center gap-3 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition-colors duration-200 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            <FcGoogle className="h-5 w-5" />
            <span>Sign in with Google</span>
          </button>
        </a>
      </div>
    </main>
  )
}
