import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Database, BarChart3, FlaskConical,
  Users, Search, ClipboardCheck, FileDown, AlertTriangle,
} from 'lucide-react'
import clsx from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/supplylens'

const NAV = [
  { to: '/',           icon: LayoutDashboard, label: 'Overview'           },
  { to: '/data',       icon: Database,        label: 'Data Workspace'     },
  { to: '/risk',       icon: BarChart3,       label: 'Material Risk'      },
  { to: '/scenario',   icon: FlaskConical,    label: 'Scenario Lab'       },
  { to: '/suppliers',  icon: Users,           label: 'Supplier Comparison'},
  { to: '/evidence',   icon: Search,          label: 'Evidence Trace'     },
  { to: '/decisions',  icon: ClipboardCheck,  label: 'Decision Review'    },
  { to: '/reports',    icon: FileDown,        label: 'Reports'            },
]

export default function Layout() {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  const dbOk = health?.database === 'connected'

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">SL</span>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">SupplyLens</p>
              <p className="text-xs text-gray-400">Shock-to-Decision</p>
            </div>
          </div>
        </div>

        {/* DB Status */}
        <div className="px-4 py-2 border-b border-gray-100">
          <div className="flex items-center gap-2 text-xs">
            <div className={clsx('w-2 h-2 rounded-full', dbOk ? 'bg-green-500' : 'bg-red-400')} />
            <span className={dbOk ? 'text-green-700' : 'text-red-600'}>
              Exasol {dbOk ? 'connected' : 'not connected'}
            </span>
            {!dbOk && (
              <a
                href="#"
                className="text-amber-600 hover:underline"
                title="See README for setup"
              >
                <AlertTriangle className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-100">
          <p className="text-xs text-gray-400">ExaThon India 2026</p>
          <p className="text-xs text-gray-400">Synthetic data only</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
