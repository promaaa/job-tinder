import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  Search,
  Filter,
  X,
  Building2,
  MapPin,
  DollarSign,
  Briefcase,
  Globe,
  ExternalLink,
  SlidersHorizontal,
  Clock,
  Check
} from 'lucide-react'

// Source colors
const SOURCE_COLORS: Record<string, string> = {
  remoteok: '#00D4AA',
  arbeitnow: '#6366F1',
  jobicy: '#F59E0B',
  himalayas: '#8B5CF6',
  linkedin: '#0A66C2',
  indeed: '#2164F3',
  glassdoor: '#0CAA41',
  wttj: '#FFE14D',
}

interface Filters {
  query: string
  status: string
  remote: string
  type: string
  seniority: string
  source: string
  location: string
  salary_min: number | null
  salary_max: number | null
  posted_within: number | null
  has_salary: boolean
  sort_by: string
}

const defaultFilters: Filters = {
  query: '',
  status: 'all',
  remote: 'any',
  type: '',
  seniority: '',
  source: '',
  location: '',
  salary_min: null,
  salary_max: null,
  posted_within: null,
  has_salary: false,
  sort_by: 'date',
}

const CRMPage = () => {
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [showFilters, setShowFilters] = useState(true)
  const [page, setPage] = useState(0)
  const limit = 25

  // Fetch filter options
  const { data: filterOptions } = useQuery({
    queryKey: ['jobs', 'filters'],
    queryFn: () => axios.get('/jobs/filters').then(res => res.data)
  })

  // Fetch jobs with filters
  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['jobs', 'filtered', filters, page],
    queryFn: () => {
      const params: Record<string, any> = {
        status: filters.status,
        limit,
        offset: page * limit,
        sort_by: filters.sort_by,
      }
      if (filters.query) params.query = filters.query
      if (filters.remote !== 'any') params.remote = filters.remote
      if (filters.type) params.type = filters.type
      if (filters.seniority) params.seniority = filters.seniority
      if (filters.source) params.source = filters.source
      if (filters.location) params.location = filters.location
      if (filters.salary_min) params.salary_min = filters.salary_min
      if (filters.salary_max) params.salary_max = filters.salary_max
      if (filters.posted_within) params.posted_within = filters.posted_within
      if (filters.has_salary) params.has_salary = true

      return axios.get('/jobs', { params }).then(res => res.data)
    }
  })

  // Reset page when filters change
  useEffect(() => {
    setPage(0)
  }, [filters])

  const updateFilter = (key: keyof Filters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const resetFilters = () => {
    setFilters(defaultFilters)
  }

  const activeFiltersCount = Object.entries(filters).filter(([key, value]) => {
    if (key === 'query' || key === 'sort_by') return false
    if (key === 'status' && value === 'all') return false
    if (key === 'remote' && value === 'any') return false
    if (key === 'has_salary' && value === false) return false
    return value !== '' && value !== null
  }).length



  const formatDate = (dateStr?: string) => {
    if (!dateStr) return null
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
      if (diffDays === 0) return 'Today'
      if (diffDays === 1) return 'Yesterday'
      if (diffDays < 7) return `${diffDays}d ago`
      return date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
    } catch {
      return null
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white font-display">Jobs Explorer</h1>
          <p className="text-[#71717A] mt-1">
            {jobsData?.total || 0} jobs found
          </p>
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm transition-all border ${showFilters
            ? 'bg-[#FF6B35]/10 text-[#FF6B35] border-[#FF6B35]/30'
            : 'bg-[#222226] text-white border-white/10 hover:bg-[#2A2A2E]'
            }`}
        >
          <SlidersHorizontal size={16} />
          Filters
          {activeFiltersCount > 0 && (
            <span className="w-5 h-5 rounded-full bg-[#FF6B35] text-white text-xs flex items-center justify-center">
              {activeFiltersCount}
            </span>
          )}
        </button>
      </div>

      {/* Search Bar */}
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#52525B]" />
          <input
            type="text"
            placeholder="Search jobs by title, company, description..."
            className="w-full bg-[#1A1A1D] border border-white/10 rounded-xl pl-11 pr-4 py-3 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
            value={filters.query}
            onChange={(e) => updateFilter('query', e.target.value)}
          />
        </div>
        <select
          value={filters.sort_by}
          onChange={(e) => updateFilter('sort_by', e.target.value)}
          className="bg-[#1A1A1D] border border-white/10 rounded-xl px-4 py-3 text-white focus:border-[#FF6B35] outline-none cursor-pointer"
        >
          <option value="date">Sort by Date</option>
          <option value="salary">Sort by Salary</option>
          <option value="company">Sort by Company</option>
        </select>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-5 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <Filter size={14} className="text-[#FF6B35]" />
              Advanced Filters
            </div>
            {activeFiltersCount > 0 && (
              <button
                onClick={resetFilters}
                className="text-xs text-[#71717A] hover:text-white flex items-center gap-1"
              >
                <X size={12} />
                Clear all
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {/* Status */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Status</label>
              <select
                value={filters.status}
                onChange={(e) => updateFilter('status', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="all">All Jobs</option>
                <option value="pending">Pending</option>
                <option value="yes">Liked</option>
                <option value="no">Passed</option>
              </select>
            </div>

            {/* Remote */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Remote</label>
              <select
                value={filters.remote}
                onChange={(e) => updateFilter('remote', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="any">Any</option>
                <option value="remote">Remote Only</option>
                <option value="office">On-site</option>
              </select>
            </div>

            {/* Employment Type */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Type</label>
              <select
                value={filters.type}
                onChange={(e) => updateFilter('type', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="">Any Type</option>
                {filterOptions?.employment_types?.map((t: string) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Seniority */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Seniority</label>
              <select
                value={filters.seniority}
                onChange={(e) => updateFilter('seniority', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="">Any Level</option>
                <option value="junior">Junior</option>
                <option value="mid">Mid-level</option>
                <option value="senior">Senior</option>
              </select>
            </div>

            {/* Source */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Source</label>
              <select
                value={filters.source}
                onChange={(e) => updateFilter('source', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="">All Sources</option>
                {filterOptions?.sources?.map((s: string) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Posted Within */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Posted</label>
              <select
                value={filters.posted_within || ''}
                onChange={(e) => updateFilter('posted_within', e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-[#FF6B35] outline-none"
              >
                <option value="">Any Time</option>
                <option value="1">Last 24h</option>
                <option value="3">Last 3 days</option>
                <option value="7">Last week</option>
                <option value="14">Last 2 weeks</option>
                <option value="30">Last month</option>
              </select>
            </div>
          </div>

          {/* Second Row: Location & Salary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Location */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Location</label>
              <input
                type="text"
                placeholder="e.g. Paris, France"
                value={filters.location}
                onChange={(e) => updateFilter('location', e.target.value)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
              />
            </div>

            {/* Min Salary */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Min Salary</label>
              <input
                type="number"
                placeholder="e.g. 50000"
                value={filters.salary_min || ''}
                onChange={(e) => updateFilter('salary_min', e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
              />
            </div>

            {/* Max Salary */}
            <div>
              <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Max Salary</label>
              <input
                type="number"
                placeholder="e.g. 100000"
                value={filters.salary_max || ''}
                onChange={(e) => updateFilter('salary_max', e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#222226] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none"
              />
            </div>

            {/* Has Salary Toggle */}
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_salary}
                  onChange={(e) => updateFilter('has_salary', e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${filters.has_salary
                  ? 'bg-[#FF6B35] border-[#FF6B35]'
                  : 'border-white/20 bg-[#222226]'
                  }`}>
                  {filters.has_salary && <Check size={12} className="text-white" />}
                </div>
                <span className="text-sm text-[#A1A1AA]">Only with salary</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Jobs List */}
      <div className="bg-[#1A1A1D] rounded-xl border border-white/5 overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 rounded-lg bg-[#FF6B35]/20 animate-pulse mx-auto mb-3" />
            <p className="text-sm text-[#52525B]">Loading jobs...</p>
          </div>
        ) : jobsData?.items?.length === 0 ? (
          <div className="p-12 text-center">
            <Search size={32} className="mx-auto mb-3 text-[#3F3F46]" />
            <p className="text-sm text-[#52525B]">No jobs match your filters.</p>
            <button onClick={resetFilters} className="mt-2 text-xs text-[#FF6B35] hover:underline">
              Clear filters
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {jobsData?.items?.map((job: any) => {
              const source = (job.source || '').replace('jobspy_', '')
              const sourceColor = SOURCE_COLORS[source] || '#71717A'

              return (
                <div key={job.id} className="p-4 hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-start gap-4">
                    {/* Source Badge */}
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-white text-[10px] font-bold uppercase shrink-0"
                      style={{ backgroundColor: sourceColor }}
                    >
                      {source.slice(0, 2)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-white truncate hover:text-[#FF6B35] transition-colors">
                            {job.title}
                          </h3>
                          <div className="flex items-center gap-3 mt-1 text-sm text-[#71717A]">
                            <span className="flex items-center gap-1">
                              <Building2 size={12} />
                              {job.company}
                            </span>
                            <span className="flex items-center gap-1">
                              <MapPin size={12} />
                              {job.location || 'Remote'}
                            </span>
                            {job.is_remote && (
                              <span className="flex items-center gap-1 text-[#3B82F6]">
                                <Globe size={12} />
                                Remote
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {/* Decision Badge */}
                          {job.decision && job.decision !== 'pending' && (
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${job.decision === 'yes'
                              ? 'bg-[#22C55E]/10 text-[#22C55E]'
                              : 'bg-[#EF4444]/10 text-[#EF4444]'
                              }`}>
                              {job.decision === 'yes' ? 'LIKED' : 'PASSED'}
                            </span>
                          )}

                          {job.url && (
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="w-8 h-8 rounded-lg bg-[#222226] flex items-center justify-center text-[#71717A] hover:text-white hover:bg-[#FF6B35] transition-all"
                            >
                              <ExternalLink size={14} />
                            </a>
                          )}
                        </div>
                      </div>

                      {/* Meta Row */}
                      <div className="flex items-center gap-3 mt-3 flex-wrap">
                        {job.salary && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#22C55E]/10 rounded text-xs text-[#22C55E] font-medium">
                            <DollarSign size={10} />
                            {job.salary}
                          </span>
                        )}

                        {job.employment_type && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#222226] rounded text-xs text-[#A1A1AA]">
                            <Briefcase size={10} />
                            {job.employment_type}
                          </span>
                        )}

                        {job.tags?.slice(0, 3).map((tag: string) => (
                          <span key={tag} className="px-2 py-0.5 bg-[#222226] rounded text-[10px] text-[#71717A]">
                            {tag}
                          </span>
                        ))}

                        <span className="ml-auto text-[10px] text-[#52525B] flex items-center gap-1">
                          <Clock size={10} />
                          {formatDate(job.fetched_at || job.published_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Pagination */}
        {jobsData && jobsData.total > limit && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-white/5">
            <span className="text-xs text-[#52525B]">
              Showing {page * limit + 1} - {Math.min((page + 1) * limit, jobsData.total)} of {jobsData.total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 text-xs bg-[#222226] text-white rounded-lg disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * limit >= jobsData.total}
                className="px-3 py-1 text-xs bg-[#222226] text-white rounded-lg disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default CRMPage
