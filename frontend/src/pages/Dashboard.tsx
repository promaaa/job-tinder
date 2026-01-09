import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  Heart,
  X,
  Clock,
  Send,
  Flame,
  TrendingUp,
  Sparkles
} from 'lucide-react'

const Dashboard = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => axios.get('/stats').then(res => res.data)
  })

  const { data: outreach } = useQuery({
    queryKey: ['outreach'],
    queryFn: () => axios.get('/outreach').then(res => res.data)
  })

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#FF6B35] to-[#F7931E] animate-pulse" />
      </div>
    )
  }

  const statCards = [
    { label: 'Total Jobs', value: stats?.total || 0, icon: TrendingUp, color: '#3B82F6' },
    { label: 'Liked', value: stats?.yes || 0, icon: Heart, color: '#22C55E' },
    { label: 'Passed', value: stats?.no || 0, icon: X, color: '#EF4444' },
    { label: 'Pending', value: stats?.pending || 0, icon: Clock, color: '#F59E0B' },
  ]

  const sentEmails = outreach?.filter((m: any) => m.status === 'sent').length || 0
  const pendingReview = stats?.pending || 0

  return (
    <div className="space-y-8">
      {/* Welcome Header with Branding */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1A1A1D] via-[#1A1A1D] to-[#FF6B35]/10 border border-white/5 p-6 lg:p-8">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-[#FF6B35]/20 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/4 w-48 h-48 bg-gradient-to-tr from-[#8B5CF6]/10 to-transparent rounded-full blur-2xl" />

        <div className="relative z-10 flex items-center justify-between gap-6">
          <div>
            <p className="text-[#71717A] text-sm mb-1">
              {new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'} 👋
            </p>
            <h1 className="text-3xl lg:text-4xl font-bold text-white font-display mb-2">
              Welcome to <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF6B35] to-[#FFB347]">JOBi</span>
            </h1>
            <p className="text-[#A1A1AA] max-w-lg">
              Your intelligent job discovery platform. Swipe through curated opportunities and build your career pipeline.
            </p>
          </div>

          {pendingReview > 0 && (
            <Link
              to="/swipe"
              className="shrink-0 inline-flex items-center gap-2 bg-gradient-to-r from-[#FF6B35] to-[#F7931E] text-white px-6 py-3 rounded-xl font-semibold text-sm hover:opacity-90 transition-all shadow-lg shadow-[#FF6B35]/25 hover:shadow-[#FF6B35]/40 hover:scale-105"
            >
              <Flame size={18} />
              Review {pendingReview} Jobs
            </Link>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="bg-[#1A1A1D] p-5 border border-white/5 rounded-xl hover:border-white/10 transition-colors group"
          >
            <div className="flex justify-between items-start mb-4">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#52525B]">{card.label}</span>
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                style={{ backgroundColor: `${card.color}15` }}
              >
                <card.icon size={16} style={{ color: card.color }} />
              </div>
            </div>
            <span className="text-3xl font-semibold text-white font-display">{card.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Correspondence */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Send size={14} className="text-[#FF6B35]" />
              Recent Outreach
            </h2>
            <Link
              to="/crm"
              className="text-[10px] font-semibold text-[#71717A] hover:text-white uppercase tracking-wider transition-colors flex items-center gap-1"
            >
              View All
              <ArrowUpRight size={10} />
            </Link>
          </div>

          <div className="bg-[#1A1A1D] rounded-xl border border-white/5 overflow-hidden divide-y divide-white/5">
            {outreach?.slice(0, 4).map((msg: any) => (
              <div key={msg.id} className="flex items-center justify-between p-4 hover:bg-white/[0.02] transition-all group">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[#222226] flex items-center justify-center text-[#71717A] group-hover:bg-[#FF6B35]/10 group-hover:text-[#FF6B35] transition-colors">
                    <Send size={14} />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">{msg.subject}</p>
                    <p className="text-xs text-[#52525B]">To: {msg.contact_name}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider ${msg.status === 'sent'
                  ? 'bg-[#22C55E]/10 text-[#22C55E]'
                  : 'bg-[#F59E0B]/10 text-[#F59E0B]'
                  }`}>
                  {msg.status}
                </span>
              </div>
            ))}
            {(!outreach || outreach.length === 0) && (
              <div className="p-8 text-center">
                <Send size={24} className="mx-auto mb-2 text-[#3F3F46]" />
                <p className="text-sm text-[#52525B]">No outreach yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* Performance Card */}
        <div className="bg-gradient-to-br from-[#1A1A1D] to-[#111113] border border-white/5 p-6 rounded-xl flex flex-col justify-between min-h-[280px] relative overflow-hidden">
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={14} className="text-[#FF6B35]" />
              <h3 className="text-sm font-semibold text-white">Outreach Goal</h3>
            </div>
            <p className="text-[10px] text-[#52525B] uppercase tracking-wider">Monthly Target</p>
          </div>

          <div className="relative z-10 space-y-1">
            <p className="text-5xl font-semibold text-white font-display">{sentEmails}</p>
            <p className="text-sm text-[#52525B]">of 50 emails sent</p>
          </div>

          <div className="relative z-10 space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="text-[#52525B]">Progress</span>
              <span className="text-[#FF6B35] font-semibold">{Math.round((sentEmails / 50) * 100)}%</span>
            </div>
            <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-gradient-to-r from-[#FF6B35] to-[#F7931E] h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min((sentEmails / 50) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Decorative */}
          <div className="absolute -bottom-16 -right-16 w-40 h-40 bg-[#FF6B35]/5 rounded-full blur-3xl pointer-events-none" />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/swipe"
          className="bg-[#1A1A1D] p-5 rounded-xl border border-white/5 hover:border-[#FF6B35]/30 hover:bg-[#FF6B35]/5 transition-all group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-xl bg-[#FF6B35]/10 flex items-center justify-center group-hover:bg-[#FF6B35]/20 transition-colors">
            <Flame size={24} className="text-[#FF6B35]" />
          </div>
          <div>
            <p className="font-semibold text-white">Discover Jobs</p>
            <p className="text-xs text-[#52525B]">Swipe through opportunities</p>
          </div>
        </Link>

        <Link
          to="/ingestion"
          className="bg-[#1A1A1D] p-5 rounded-xl border border-white/5 hover:border-[#22C55E]/30 hover:bg-[#22C55E]/5 transition-all group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-xl bg-[#22C55E]/10 flex items-center justify-center group-hover:bg-[#22C55E]/20 transition-colors">
            <TrendingUp size={24} className="text-[#22C55E]" />
          </div>
          <div>
            <p className="font-semibold text-white">Harvest Jobs</p>
            <p className="text-xs text-[#52525B]">Sync with job boards</p>
          </div>
        </Link>

        <Link
          to="/profile"
          className="bg-[#1A1A1D] p-5 rounded-xl border border-white/5 hover:border-[#3B82F6]/30 hover:bg-[#3B82F6]/5 transition-all group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-xl bg-[#3B82F6]/10 flex items-center justify-center group-hover:bg-[#3B82F6]/20 transition-colors">
            <Sparkles size={24} className="text-[#3B82F6]" />
          </div>
          <div>
            <p className="font-semibold text-white">Your Profile</p>
            <p className="text-xs text-[#52525B]">Manage CV & settings</p>
          </div>
        </Link>
      </div>
    </div>
  )
}

export default Dashboard
