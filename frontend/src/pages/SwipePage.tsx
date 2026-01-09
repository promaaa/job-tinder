import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Heart,
  MapPin,
  DollarSign,
  Building2,
  Briefcase,
  Clock,
  ExternalLink,
  RotateCcw,
  Sparkles,
  ChevronDown,
  Globe
} from 'lucide-react'
import DOMPurify from 'dompurify'

const SwipePage = () => {
  const queryClient = useQueryClient()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showFullDescription, setShowFullDescription] = useState(false)
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null)
  const isAnimating = useRef(false)

  const { data: jobsResponse, isLoading } = useQuery({
    queryKey: ['jobs', 'pending'],
    queryFn: () => axios.get('/jobs?status=pending').then(res => res.data)
  })

  const swipeMutation = useMutation({
    mutationFn: (payload: { job_id: string, decision: 'yes' | 'no' }) =>
      axios.post('/swipes', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    }
  })

  const jobs = jobsResponse?.items || []
  const currentJob = jobs[currentIndex]
  const nextJob = jobs[currentIndex + 1]

  const handleSwipe = (decision: 'yes' | 'no') => {
    if (!currentJob || isAnimating.current) return

    isAnimating.current = true
    setSwipeDirection(decision === 'yes' ? 'right' : 'left')

    // Submit the swipe
    swipeMutation.mutate({ job_id: currentJob.id, decision })

    // Wait for animation then move to next
    setTimeout(() => {
      setCurrentIndex(prev => prev + 1)
      setSwipeDirection(null)
      setShowFullDescription(false)
      isAnimating.current = false
    }, 250)
  }

  const handleUndo = () => {
    if (currentIndex > 0 && !isAnimating.current) {
      setCurrentIndex(prev => prev - 1)
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') handleSwipe('no')
      if (e.key === 'ArrowRight') handleSwipe('yes')
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentJob])

  if (isLoading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#FF6B35] to-[#F7931E] animate-pulse" />
        <p className="mt-6 text-sm font-medium text-[#71717A]">Loading jobs...</p>
      </div>
    )
  }

  if (!currentJob || currentIndex >= jobs.length) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center">
        <div className="w-20 h-20 rounded-full bg-[#FF6B35]/10 flex items-center justify-center mb-6">
          <Sparkles size={32} className="text-[#FF6B35]" />
        </div>
        <h2 className="text-2xl font-semibold text-white mb-2">All caught up!</h2>
        <p className="text-[#71717A] text-center max-w-sm mb-6">
          You've reviewed all available jobs. Check back later for new opportunities.
        </p>
        <button
          onClick={() => setCurrentIndex(0)}
          className="px-6 py-3 bg-[#222226] text-white rounded-xl font-semibold hover:bg-[#2A2A2E] transition-all border border-white/10 flex items-center gap-2"
        >
          <RotateCcw size={16} />
          Start Over
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center py-4">
      {/* Progress */}
      <div className="w-full max-w-md mb-6">
        <div className="flex justify-between text-xs text-[#71717A] mb-2">
          <span>{currentIndex + 1} / {jobs.length}</span>
          <span>{jobs.length - currentIndex - 1} remaining</span>
        </div>
        <div className="h-1 bg-[#222226] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#FF6B35] to-[#F7931E] transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / jobs.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Card Container */}
      <div className="relative w-full max-w-md h-[480px] mb-8">
        {/* Next Card Preview */}
        {nextJob && (
          <div className="absolute inset-0 scale-[0.92] translate-y-3 opacity-40">
            <div className="w-full h-full bg-[#1A1A1D] rounded-2xl border border-white/5" />
          </div>
        )}

        {/* Current Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentJob.id}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1, x: 0 }}
            exit={{
              x: swipeDirection === 'right' ? 300 : swipeDirection === 'left' ? -300 : 0,
              opacity: 0,
              rotate: swipeDirection === 'right' ? 10 : swipeDirection === 'left' ? -10 : 0
            }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="absolute inset-0 bg-[#1A1A1D] rounded-2xl border border-white/10 overflow-hidden shadow-xl"
          >
            {/* Header */}
            <div className="bg-gradient-to-br from-[#222226] to-[#1A1A1D] p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
                    <Building2 size={22} className="text-[#A1A1AA]" />
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold text-[#52525B] uppercase tracking-wider">Company</p>
                    <p className="text-white font-semibold">{currentJob.company}</p>
                  </div>
                </div>
                {currentJob.url && (
                  <a
                    href={currentJob.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center border border-white/10 hover:bg-white/10 transition-colors"
                  >
                    <ExternalLink size={16} className="text-[#A1A1AA]" />
                  </a>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="p-5 space-y-4 h-[calc(100%-88px)] overflow-y-auto">
              <h2 className="text-xl font-semibold text-white leading-tight">
                {currentJob.title}
              </h2>

              {/* Tags */}
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#222226] rounded-lg text-xs text-[#A1A1AA]">
                  <MapPin size={12} className="text-[#FF6B35]" />
                  {currentJob.location || 'Remote'}
                </span>

                {currentJob.salary && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#22C55E]/10 rounded-lg text-xs text-[#22C55E]">
                    <DollarSign size={12} />
                    {currentJob.salary}
                  </span>
                )}

                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#222226] rounded-lg text-xs text-[#A1A1AA]">
                  <Briefcase size={12} />
                  {currentJob.employment_type || 'Full-time'}
                </span>

                {currentJob.is_remote && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#3B82F6]/10 rounded-lg text-xs text-[#3B82F6]">
                    <Globe size={12} />
                    Remote
                  </span>
                )}
              </div>

              {/* Description */}
              <div>
                <div
                  className={`prose prose-sm prose-invert max-w-none text-[#A1A1AA] text-sm leading-relaxed ${showFullDescription ? '' : 'line-clamp-5'}`}
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(currentJob.description || 'No description available.') }}
                />

                {currentJob.description && currentJob.description.length > 200 && (
                  <button
                    onClick={() => setShowFullDescription(!showFullDescription)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-[#FF6B35] mt-2 hover:text-[#FF8255]"
                  >
                    {showFullDescription ? 'Show less' : 'Read more'}
                    <ChevronDown size={14} className={showFullDescription ? 'rotate-180' : ''} />
                  </button>
                )}
              </div>

              {/* Skills */}
              {currentJob.tags && currentJob.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {currentJob.tags.slice(0, 6).map((tag: string) => (
                    <span key={tag} className="text-[10px] font-medium text-[#71717A] bg-[#222226] px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Posted */}
              <div className="flex items-center gap-1.5 text-[10px] text-[#52525B]">
                <Clock size={10} />
                <span>Posted {currentJob.published_at ? new Date(currentJob.published_at).toLocaleDateString() : 'recently'}</span>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleUndo}
          disabled={currentIndex === 0}
          className="w-12 h-12 rounded-full bg-[#1A1A1D] border border-white/10 flex items-center justify-center text-[#71717A] hover:bg-[#222226] disabled:opacity-30 transition-all"
        >
          <RotateCcw size={18} />
        </button>

        <button
          onClick={() => handleSwipe('no')}
          className="w-16 h-16 rounded-full bg-[#1A1A1D] border-2 border-[#EF4444]/30 flex items-center justify-center text-[#EF4444] hover:bg-[#EF4444]/10 hover:border-[#EF4444]/50 transition-all active:scale-95"
        >
          <X size={28} strokeWidth={3} />
        </button>

        <button
          onClick={() => handleSwipe('yes')}
          className="w-16 h-16 rounded-full bg-gradient-to-br from-[#22C55E] to-[#16A34A] flex items-center justify-center text-white shadow-lg shadow-[#22C55E]/20 hover:shadow-xl transition-all active:scale-95"
        >
          <Heart size={28} fill="currentColor" />
        </button>

        <button
          className="w-12 h-12 rounded-full bg-[#1A1A1D] border border-white/10 flex items-center justify-center text-[#FF6B35] hover:bg-[#FF6B35]/10 transition-all"
        >
          <Sparkles size={18} />
        </button>
      </div>

      {/* Hint */}
      <p className="text-[10px] text-[#52525B] mt-6">
        Use <kbd className="px-1.5 py-0.5 bg-[#1A1A1D] rounded border border-white/10 mx-1">←</kbd>
        <kbd className="px-1.5 py-0.5 bg-[#1A1A1D] rounded border border-white/10 mx-1">→</kbd>
        arrow keys or click buttons
      </p>
    </div>
  )
}

export default SwipePage
