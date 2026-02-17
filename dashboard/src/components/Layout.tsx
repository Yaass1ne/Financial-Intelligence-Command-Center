import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  BarChart3,
  FileText,
  Receipt,
  Bell,
  Zap,
  MessageSquare
} from 'lucide-react'
import { cn } from '../lib/utils'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Budget Augmented', href: '/', icon: BarChart3 },
  { name: 'Contracts & Clauses', href: '/contracts', icon: FileText },
  { name: 'Invoices & Treasury', href: '/invoices', icon: Receipt },
  { name: 'Alerts & Recommendations', href: '/alerts', icon: Bell },
  { name: 'Simulations', href: '/simulations', icon: Zap },
  { name: 'AI Assistant', href: '/chat', icon: MessageSquare },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-primary-600 rounded-lg">
                <span className="text-white font-bold text-xl">F</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">FINCENTER</h1>
                <p className="text-sm text-gray-500">Financial Intelligence Command Center</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">Financial Controller</p>
                <p className="text-xs text-gray-500">Last sync: 2 min ago</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="px-6">
          <div className="flex space-x-8">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center space-x-2 px-3 py-4 text-sm font-medium border-b-2 transition-colors",
                    isActive
                      ? "border-primary-600 text-primary-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="px-6 py-8">
        {children}
      </main>
    </div>
  )
}
