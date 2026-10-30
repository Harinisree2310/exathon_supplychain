import React, { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  AlertTriangle, BarChart3, ClipboardCheck, Database, FileDown,
  FlaskConical, LayoutDashboard, Menu, Search, ShieldCheck, Users, X,
} from 'lucide-react'
import clsx from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../api/supplylens'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Overview' },
  { to: '/data',      icon: Database,        label: 'Data workspace' },
  { to: '/risk',      icon: BarChart3,       label: 'Material risk' },
  { to: '/scenario',  icon: FlaskConical,    label: 'Scenario lab' },
  { to: '/suppliers', icon: Users,           label: 'Suppliers' },
  { to: '/evidence',  icon: Search,          label: 'Evidence trace' },
  { to: '/decisions', icon: ClipboardCheck,  label: 'Decision review' },
  { to: '/reports',   icon: FileDown,         label: 'Reports' },
]

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  })

  const dbOk = health?.database === 'connected'
  const page = NAV.find(({ to }) => to === '/'
    ? location.pathname === '/'
    : location.pathname.startsWith(to)) ?? NAV[0]
  const statusLabel = dbOk ? 'Database connected' : isError ? 'Database unavailable' : 'Connecting to database'

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={clsx('app-sidebar', mobileOpen && 'app-sidebar-open')}>
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true">S</div>
          <div className="min-w-0">
            <p className="brand-name">SupplyLens</p>
            <p className="brand-caption">PROCUREMENT INTELLIGENCE</p>
          </div>
          <button
            type="button"
            className="sidebar-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="sidebar-status" role="status" aria-live="polite">
          <span className={clsx('status-indicator', dbOk ? 'status-connected' : isError ? 'status-error' : 'status-pending')} />
          <span>{statusLabel}</span>
          {!dbOk && isError && <AlertTriangle size={14} className="ml-auto text-amber-300" />}
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          <p className="nav-section-label">WORKSPACE</p>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => clsx('nav-link', isActive && 'nav-link-active')}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-footer-icon"><ShieldCheck size={16} /></div>
          <div>
            <p className="sidebar-footer-title">Demo workspace</p>
            <p className="sidebar-footer-caption">Synthetic data only</p>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="topbar-leading">
            <button
              type="button"
              className="menu-toggle"
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              <span>Workspace</span>
              <span className="breadcrumb-divider">/</span>
              <span className="breadcrumb-current">{page.label}</span>
            </div>
          </div>
          <div className="topbar-meta">
            <span className={clsx('topbar-status-dot', dbOk ? 'status-connected' : isError ? 'status-error' : 'status-pending')} />
            <span>{dbOk ? 'Exasol live' : isError ? 'Exasol offline' : 'Connecting'}</span>
            <span className="topbar-divider" />
            <span className="topbar-workspace">SL</span>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
