import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
  Download,
  Database,
  Play,
  Loader2,
  Activity,
  ExternalLink,
  Building2,
  MapPin,
  Zap,
  Globe,
  Code,
  Briefcase,
  RefreshCw,
  Search,
  Layers,
  Shield,
  Palette,
  Rocket,
  Server,
  Brain
} from 'lucide-react'

// Source meta with colors
const SOURCE_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  remoteok: { color: '#00D4AA', icon: <Globe size={14} />, label: 'RemoteOK' },
  arbeitnow: { color: '#6366F1', icon: <Briefcase size={14} />, label: 'Arbeitnow' },
  jobicy: { color: '#F59E0B', icon: <Globe size={14} />, label: 'Jobicy' },
  himalayas: { color: '#8B5CF6', icon: <Globe size={14} />, label: 'Himalayas' },
  findwork: { color: '#EC4899', icon: <Code size={14} />, label: 'Findwork' },
  wttj: { color: '#FFE14D', icon: <Building2 size={14} />, label: 'WTTJ' },
  linkedin: { color: '#0A66C2', icon: <Briefcase size={14} />, label: 'LinkedIn' },
  indeed: { color: '#2164F3', icon: <Briefcase size={14} />, label: 'Indeed' },
  glassdoor: { color: '#0CAA41', icon: <Building2 size={14} />, label: 'Glassdoor' },
  jobteaser: { color: '#FF6B6B', icon: <Briefcase size={14} />, label: 'JobTeaser' },
  france_travail: { color: '#003DA5', icon: <Building2 size={14} />, label: 'France Travail' },
  adzuna: { color: '#60D937', icon: <Briefcase size={14} />, label: 'Adzuna' },
}

// Profile icons
const PROFILE_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  software_engineering: { icon: <Code size={16} />, color: '#3B82F6', label: 'Software Engineering' },
  data: { icon: <Brain size={16} />, color: '#8B5CF6', label: 'Data & ML' },
  devops_cloud: { icon: <Server size={16} />, color: '#F59E0B', label: 'DevOps & Cloud' },
  security: { icon: <Shield size={16} />, color: '#EF4444', label: 'Security' },
  product_design: { icon: <Palette size={16} />, color: '#EC4899', label: 'Product & Design' },
  startup_tech: { icon: <Rocket size={16} />, color: '#22C55E', label: 'Startup' },
}

const IngestionPage = () => {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [location, setLocation] = useState('')
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [selectedProfile, setSelectedProfile] = useState<string>('software_engineering')

  // Scheduler Status
  const { data: schedulerStatus } = useQuery({
    queryKey: ['scheduler', 'status'],
    queryFn: () => axios.get('/scheduler/status').then(res => res.data)
  })

  // Available Sources
  const { data: sourcesData } = useQuery({
    queryKey: ['sources'],
    queryFn: () => axios.get('/sources').then(res => res.data)
  })

  // Available Profiles
  const { data: profilesData } = useQuery({
    queryKey: ['scheduler', 'profiles'],
    queryFn: () => axios.get('/scheduler/profiles').then(res => res.data)
  })

  // Recent Jobs
  const { data: recentJobsData, refetch: refetchRecentJobs } = useQuery({
    queryKey: ['jobs', 'recent'],
    queryFn: () => axios.get('/jobs/recent?limit=20').then(res => res.data),
    refetchInterval: 10000,
  })

  // Initialize selected sources
  useEffect(() => {
    if (sourcesData?.sources && selectedSources.length === 0) {
      const free = sourcesData.sources
        .filter((s: any) => s.status === 'available' || s.status === 'scraper')
        .map((s: any) => s.name)
      setSelectedSources(free)
    }
  }, [sourcesData])

  // Trigger Fetch with profile
  const fetchMutation = useMutation({
    mutationFn: () => axios.post('/scheduler/fetch', null, {
      params: {
        sources: selectedSources.join(','),
        profile: selectedProfile,
      }
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setTimeout(() => refetchRecentJobs(), 1500)
    }
  })

  // Full multi-profile fetch
  const fullFetchMutation = useMutation({
    mutationFn: () => axios.post('/scheduler/fetch/full'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduler', 'status'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setTimeout(() => refetchRecentJobs(), 2000)
    }
  })

  // Search and Import
  const searchImportMutation = useMutation({
    mutationFn: (params: { q: string, location?: string, sources?: string }) =>
      axios.post('/search/import', null, { params }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      refetchRecentJobs()
    }
  })

  const isSyncing = fetchMutation.isPending || searchImportMutation.isPending || fullFetchMutation.isPending

  const handleSearchImport = (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchTerm) return
    searchImportMutation.mutate({
      q: searchTerm,
      location,
      sources: selectedSources.join(',')
    })
  }

  const toggleSource = (name: string) => {
    if (isSyncing) return
    setSelectedSources(prev =>
      prev.includes(name) ? prev.filter(s => s !== name) : [...prev, name]
    )
  }

  const selectAllFree = () => {
    const free = sourcesData?.sources
      ?.filter((s: any) => s.free)
      ?.map((s: any) => s.name) || []
    setSelectedSources(free)
  }

  // Extract source from job URL
  const getJobSource = (job: any): string => {
    if (job.source) return job.source.replace('jobspy_', '')
    if (job.url) {
      const url = job.url.toLowerCase()
      if (url.includes('remoteok')) return 'remoteok'
      if (url.includes('linkedin')) return 'linkedin'
      if (url.includes('indeed')) return 'indeed'
      if (url.includes('glassdoor')) return 'glassdoor'
      if (url.includes('welcometothejungle') || url.includes('wttj')) return 'wttj'
      if (url.includes('arbeitnow')) return 'arbeitnow'
      if (url.includes('jobicy')) return 'jobicy'
      if (url.includes('himalayas')) return 'himalayas'
    }
    return 'unknown'
  }

  // Format relative time
  const formatRelativeTime = (dateStr: string | undefined) => {
    if (!dateStr) return '—'
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMins / 60)
      const diffDays = Math.floor(diffHours / 24)

      if (diffMins < 1) return 'now'
      if (diffMins < 60) return `${diffMins}m`
      if (diffHours < 24) return `${diffHours}h`
      if (diffDays < 7) return `${diffDays}d`
      return date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
    } catch {
      return '—'
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-2 h-2 rounded-full ${isSyncing ? 'bg-[#FF6B35] animate-pulse' : 'bg-[#52525B]'}`} />
            <span className="text-xs font-semibold text-[#71717A] uppercase tracking-wider">Data Pipeline</span>
          </div>
          <h1 className="text-3xl font-semibold text-white font-display">Harvest</h1>
          <p className="text-[#71717A] mt-1">Scrape job boards with intelligent profiles.</p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => fullFetchMutation.mutate()}
            disabled={isSyncing}
            className="inline-flex items-center gap-2 bg-[#222226] text-white px-4 py-2.5 rounded-xl font-semibold text-sm transition-all hover:bg-[#2A2A2E] disabled:opacity-50 border border-white/10"
          >
            {fullFetchMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Layers size={16} />}
            <span>Full Sync</span>
          </button>

          <button
            onClick={() => fetchMutation.mutate()}
            disabled={isSyncing || selectedSources.length === 0}
            className="inline-flex items-center gap-2 bg-gradient-to-r from-[#FF6B35] to-[#F7931E] text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50 shadow-lg shadow-[#FF6B35]/20"
          >
            {fetchMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
            <span>Run Profile</span>
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#1A1A1D] rounded-xl p-4 border border-white/5">
          <p className="text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-1">Last Sync</p>
          <p className="text-lg font-semibold text-white">
            {schedulerStatus?.last_fetch
              ? new Date(schedulerStatus.last_fetch).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : '--:--'}
          </p>
        </div>
        <div className="bg-[#1A1A1D] rounded-xl p-4 border border-white/5">
          <p className="text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-1">Total Harvested</p>
          <p className="text-lg font-semibold text-[#FF6B35]">{schedulerStatus?.total_fetched || 0}</p>
        </div>
        <div className="bg-[#1A1A1D] rounded-xl p-4 border border-white/5">
          <p className="text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-1">Active Sources</p>
          <p className="text-lg font-semibold text-[#22C55E]">{selectedSources.length}</p>
        </div>
        <div className="bg-[#1A1A1D] rounded-xl p-4 border border-white/5">
          <p className="text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-1">Profile</p>
          <p className="text-lg font-semibold text-[#3B82F6] capitalize">{selectedProfile.replace('_', ' ')}</p>
        </div>
      </div>

      {/* Profiles */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-[#FF6B35]" />
          <h3 className="text-sm font-semibold text-white">Search Profiles</h3>
          <span className="text-xs text-[#52525B]">— Select a category to focus your search</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {Object.entries(PROFILE_META).map(([key, meta]) => (
            <button
              key={key}
              onClick={() => setSelectedProfile(key)}
              disabled={isSyncing}
              className={`p-3 rounded-xl border transition-all text-left ${selectedProfile === key
                ? 'bg-white/5 border-white/20'
                : 'bg-[#1A1A1D] border-white/5 hover:border-white/10'
                }`}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-white"
                  style={{ backgroundColor: `${meta.color}20`, color: meta.color }}
                >
                  {meta.icon}
                </div>
                <div>
                  <p className="font-medium text-white text-xs">{meta.label}</p>
                  <p className="text-[9px] text-[#52525B]">
                    {profilesData?.profiles?.find((p: any) => p.name === key)?.queries_count || 0} queries
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Sources Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-[#FF6B35]" />
            <h3 className="text-sm font-semibold text-white">Sources</h3>
            <span className="text-xs text-[#52525B]">({sourcesData?.sources?.length || 0})</span>
          </div>
          <button
            onClick={selectAllFree}
            className="text-[10px] font-semibold text-[#71717A] hover:text-white uppercase tracking-wider transition-colors"
          >
            Select All
          </button>
        </div>

        <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
          {sourcesData?.sources?.map((src: any) => {
            const isActiveScrape = isSyncing && selectedSources.includes(src.name);
            const meta = SOURCE_META[src.name] || { color: '#71717A', icon: <Globe size={14} />, label: src.name };
            const isSelected = selectedSources.includes(src.name);
            const isDisabled = src.status === 'needs_config';

            return (
              <button
                key={src.name}
                onClick={() => toggleSource(src.name)}
                disabled={isDisabled}
                className={`relative p-2 rounded-lg border transition-all ${isSelected
                  ? 'bg-white/5 border-white/20'
                  : isDisabled
                    ? 'bg-[#1A1A1D] border-white/5 opacity-40 cursor-not-allowed'
                    : 'bg-[#1A1A1D] border-white/5 hover:border-white/10'
                  } ${isActiveScrape ? 'ring-1 ring-[#FF6B35]' : ''}`}
                title={meta.label}
              >
                <div
                  className="w-6 h-6 rounded-md flex items-center justify-center text-white mx-auto"
                  style={{ backgroundColor: meta.color }}
                >
                  {isActiveScrape ? <Loader2 size={12} className="animate-spin" /> : meta.icon}
                </div>
                {isSelected && !isDisabled && (
                  <div className="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-[#FF6B35]" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search Form */}
      <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Search size={14} className="text-[#FF6B35]" />
          <h3 className="text-sm font-semibold text-white">Custom Search</h3>
        </div>

        <form onSubmit={handleSearchImport} className="flex gap-3">
          <input
            type="text"
            placeholder="Job title or keywords..."
            className="flex-1 bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <input
            type="text"
            placeholder="Location"
            className="w-40 bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <button
            type="submit"
            disabled={searchImportMutation.isPending || !searchTerm}
            className="px-5 bg-[#222226] text-white rounded-lg font-semibold text-sm flex items-center gap-2 hover:bg-[#2A2A2E] transition-all border border-white/10 disabled:opacity-50"
          >
            {searchImportMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            Import
          </button>
        </form>
      </div>

      {/* Recent Jobs Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database size={14} className="text-[#FF6B35]" />
            <h3 className="text-sm font-semibold text-white">Recently Harvested</h3>
            <span className="text-xs text-[#52525B]">({recentJobsData?.count || 0})</span>
          </div>
          <button
            onClick={() => refetchRecentJobs()}
            className="text-[10px] font-semibold text-[#71717A] hover:text-white uppercase tracking-wider transition-colors flex items-center gap-1"
          >
            <RefreshCw size={10} />
            Refresh
          </button>
        </div>

        <div className="bg-[#1A1A1D] rounded-xl border border-white/5 overflow-hidden">
          <div className="max-h-[450px] overflow-y-auto">
            {(!recentJobsData?.items || recentJobsData.items.length === 0) ? (
              <div className="px-4 py-12 text-center">
                <Database size={24} className="mx-auto mb-3 text-[#3F3F46]" />
                <p className="text-sm text-[#52525B]">No jobs harvested yet.</p>
                <p className="text-xs text-[#3F3F46] mt-1">Select a profile and run a sync.</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {recentJobsData.items.map((job: any) => {
                  const source = getJobSource(job)
                  const meta = SOURCE_META[source] || { color: '#71717A', icon: <Globe size={10} />, label: source }

                  return (
                    <div key={job.id} className="flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors group">
                      {/* Source */}
                      <div
                        className="w-7 h-7 rounded-md flex items-center justify-center text-white shrink-0"
                        style={{ backgroundColor: meta.color }}
                        title={meta.label}
                      >
                        {meta.icon}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-white text-sm truncate group-hover:text-[#FF6B35] transition-colors">
                          {job.title}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-[#71717A]">
                          <span className="flex items-center gap-1 truncate">
                            <Building2 size={10} />
                            {job.company || 'Unknown'}
                          </span>
                          <span className="flex items-center gap-1">
                            <MapPin size={10} />
                            {job.location || 'Remote'}
                          </span>
                          {job.salary && (
                            <span className="text-[#22C55E] font-medium">{job.salary}</span>
                          )}
                        </div>
                      </div>

                      {/* Meta */}
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] text-[#52525B]">
                          {formatRelativeTime(job.fetched_at || job.published_at)}
                        </span>
                        {job.url && (
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-6 h-6 rounded-md bg-[#222226] flex items-center justify-center text-[#71717A] hover:text-white hover:bg-[#FF6B35] transition-all"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default IngestionPage
