import type {Metadata} from 'next'
import {Inter} from 'next/font/google'
import './global.css'
import {BrandProvider} from '@/components/organisms/BrandProvider'

const inter = Inter({subsets: ['latin']})

export const metadata: Metadata = {
  title: 'dbt column lineage',
  description: 'dbt column lineage visualization tool for data analysts and engineers'
}

export default function RootLayout({children,}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang='en'>
    <body className={inter.className}><BrandProvider>{children}</BrandProvider></body>
    </html>
  )
}