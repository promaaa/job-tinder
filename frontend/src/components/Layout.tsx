import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutGrid,
  Flame,
  Search,
  User,
  Download,
  Sparkles
} from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

// Brand Logo Component
const JobiLogo = ({ size = 32 }: { size?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Background circle with gradient */}
    <defs>
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#FF6B35" />
        <stop offset="50%" stopColor="#F7931E" />
        <stop offset="100%" stopColor="#FFB347" />
      </linearGradient>
      <linearGradient id="sparkGradient" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#FFFFFF" />
        <stop offset="100%" stopColor="#FFE4B5" />
      </linearGradient>
    </defs>

    {/* Main circle */}
    <circle cx="20" cy="20" r="18" fill="url(#logoGradient)" />

    {/* Letter J stylized */}
    <path
      d="M24 12V24C24 26.2091 22.2091 28 20 28C17.7909 28 16 26.2091 16 24V22"
      stroke="white"
      strokeWidth="3.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />

    {/* Spark/dot accent */}
    <circle cx="24" cy="12" r="2" fill="url(#sparkGradient)" />
  </svg>
)

// Brand wordmark
const JobiWordmark = ({ className = "" }: { className?: string }) => (
  <span className={`font-display font-bold tracking-tight ${className}`}>
    <span className="text-white">JOB</span>
    <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF6B35] to-[#FFB347]">i</span>
  </span>
)

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutGrid },
    { name: 'Discover', path: '/swipe', icon: Flame },
    { name: 'Harvest', path: '/ingestion', icon: Download },
    { name: 'Explore', path: '/crm', icon: Search },
    { name: 'Profile', path: '/profile', icon: User },
  ]

  return (
    <div className="flex h-screen w-full bg-[#0A0A0B] overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-[72px] flex flex-col items-center py-6 bg-[#0A0A0B] border-r border-white/[0.06] shrink-0 z-20">
        {/* Logo */}
        <Link to="/" className="mb-8 group">
          <div className="relative">
            <JobiLogo size={40} />
            {/* Glow effect on hover */}
            <div className="absolute inset-0 rounded-full bg-[#FF6B35]/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </div>
        </Link>

        {/* Navigation */}
        <nav className="flex-1 flex flex-col items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative group w-11 h-11 flex items-center justify-center rounded-xl transition-all duration-200 ${isActive
                  ? 'bg-white/10 text-white'
                  : 'text-[#71717A] hover:text-white hover:bg-white/5'
                  }`}
                title={item.name}
              >
                <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />

                {/* Active indicator */}
                {isActive && (
                  <div className="absolute -left-[1px] top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gradient-to-b from-[#FF6B35] to-[#FFB347] rounded-r-full" />
                )}

                {/* Tooltip */}
                <div className="absolute left-full ml-3 px-2.5 py-1.5 bg-[#1A1A1D] text-white text-xs font-medium rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap shadow-xl border border-white/10 z-50">
                  {item.name}
                  <div className="absolute left-0 top-1/2 -translate-x-1 -translate-y-1/2 w-2 h-2 bg-[#1A1A1D] rotate-45 border-l border-b border-white/10" />
                </div>
              </Link>
            )
          })}
        </nav>

        {/* Premium badge */}
        <div className="mt-auto space-y-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#8B5CF6] to-[#EC4899] flex items-center justify-center text-white cursor-pointer hover:scale-105 transition-transform" title="Pro Features">
            <Sparkles size={16} />
          </div>
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] flex items-center justify-center text-white text-sm font-semibold cursor-pointer hover:ring-2 hover:ring-white/20 transition-all">
            U
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 px-6 flex items-center justify-between border-b border-white/[0.06] shrink-0 bg-[#0A0A0B]/80 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            {/* Breadcrumb with branding */}
            <JobiWordmark className="text-lg" />
            <span className="text-[#3F3F46]">/</span>
            <span className="font-medium text-white">
              {navItems.find(item => item.path === location.pathname)?.name || 'Dashboard'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Status indicator */}
            <div className="h-8 px-3 rounded-lg bg-[#22C55E]/10 text-[#22C55E] text-xs font-semibold flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-[#22C55E] animate-pulse" />
              Connected
            </div>

            {/* Version badge */}
            <div className="hidden md:flex h-8 px-3 rounded-lg bg-white/5 text-[#71717A] text-xs font-medium items-center">
              v1.0
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto bg-[#111113]">
          <div className="max-w-7xl mx-auto px-6 lg:px-8 py-8">
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}

export default Layout
