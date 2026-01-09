import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import {
    CheckCircle2,
    FileText,
    UploadCloud,
    Mail,
    Phone,
    Save,
    Zap,
    AlertCircle,
    Linkedin,
    Github,
    Globe,
    Send,
    Settings,
    Shield,
    ExternalLink,
    Clock,
    Check,
    X
} from 'lucide-react'

const ProfilePage = () => {
    const queryClient = useQueryClient()
    const [isSuccess, setIsSuccess] = useState(false)
    const [activeTab, setActiveTab] = useState<'profile' | 'autoapply' | 'history'>('profile')

    // Fetch profile
    const { data: profile, isLoading } = useQuery({
        queryKey: ['profile'],
        queryFn: () => axios.get('/profile').then(res => res.data)
    })

    // Fetch auto-apply status
    const { data: autoApplyStatus } = useQuery({
        queryKey: ['autoapply', 'status'],
        queryFn: () => axios.get('/profile/auto-apply/status').then(res => res.data)
    })

    // Fetch applications history
    const { data: applications } = useQuery({
        queryKey: ['applications'],
        queryFn: () => axios.get('/applications').then(res => res.data),
        enabled: activeTab === 'history',
    })

    // Save profile mutation
    const saveMutation = useMutation({
        mutationFn: (params: Record<string, any>) => axios.put('/profile', null, { params }),
        onSuccess: () => {
            setIsSuccess(true)
            setTimeout(() => setIsSuccess(false), 3000)
            queryClient.invalidateQueries({ queryKey: ['profile'] })
            queryClient.invalidateQueries({ queryKey: ['autoapply'] })
        }
    })

    // Upload CV mutation
    const uploadMutation = useMutation({
        mutationFn: (file: File) => {
            const formData = new FormData()
            formData.append('cv', file)
            return axios.post('/profile/cv', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['profile'] })
            queryClient.invalidateQueries({ queryKey: ['autoapply'] })
        }
    })

    // Toggle auto-apply mutation
    const toggleAutoApply = useMutation({
        mutationFn: (enabled: boolean) => axios.post('/profile/auto-apply/toggle', null, { params: { enabled } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['profile'] })
            queryClient.invalidateQueries({ queryKey: ['autoapply'] })
        }
    })

    if (isLoading) {
        return (
            <div className="min-h-[50vh] flex items-center justify-center">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#FF6B35] to-[#F7931E] animate-pulse" />
            </div>
        )
    }

    const handleSaveProfile = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        const formData = new FormData(e.currentTarget)
        const data: Record<string, any> = {}
        formData.forEach((value, key) => {
            if (value) data[key] = value
        })
        saveMutation.mutate(data)
    }

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            uploadMutation.mutate(e.target.files[0])
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-semibold text-white font-display">Profile & Settings</h1>
                    <p className="text-[#71717A] mt-1">Configure your profile and auto-apply settings.</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-white/10 pb-px">
                {[
                    { key: 'profile', label: 'Profile', icon: Settings },
                    { key: 'autoapply', label: 'Auto-Apply', icon: Zap },
                    { key: 'history', label: 'Applications', icon: Send },
                ].map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as any)}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${activeTab === tab.key
                                ? 'bg-[#1A1A1D] text-white border-b-2 border-[#FF6B35]'
                                : 'text-[#71717A] hover:text-white'
                            }`}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Profile Tab */}
            {activeTab === 'profile' && (
                <form onSubmit={handleSaveProfile} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left: CV Upload */}
                    <div className="space-y-4">
                        <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-5">
                            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                <FileText size={16} className="text-[#FF6B35]" />
                                Curriculum Vitae
                            </h3>

                            {profile?.cv_filename ? (
                                <div className="bg-[#222226] p-4 rounded-lg flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-lg bg-[#FF6B35]/10 flex items-center justify-center text-[#FF6B35]">
                                        <FileText size={20} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-white text-sm truncate">{profile.cv_filename}</p>
                                        <p className="text-[10px] text-[#52525B] uppercase">PDF Document</p>
                                    </div>
                                    <CheckCircle2 size={16} className="text-[#22C55E]" />
                                </div>
                            ) : (
                                <label className="block cursor-pointer">
                                    <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.doc,.docx" />
                                    <div className="border-2 border-dashed border-white/10 rounded-lg p-6 text-center hover:border-[#FF6B35]/50 transition-colors">
                                        <UploadCloud size={32} className="mx-auto mb-2 text-[#52525B]" />
                                        <p className="text-sm text-[#71717A]">Click to upload your CV</p>
                                        <p className="text-[10px] text-[#52525B] mt-1">PDF, DOC, DOCX</p>
                                    </div>
                                </label>
                            )}

                            {uploadMutation.isPending && (
                                <p className="text-xs text-[#FF6B35] mt-2 animate-pulse">Uploading...</p>
                            )}
                        </div>

                        {/* Stats */}
                        <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-5">
                            <h3 className="text-sm font-semibold text-white mb-4">Statistics</h3>
                            <div className="space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-[#71717A]">Applications Sent</span>
                                    <span className="text-white font-semibold">{profile?.applications_count || 0}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-[#71717A]">Auto-Apply</span>
                                    <span className={`font-semibold ${profile?.auto_apply_enabled ? 'text-[#22C55E]' : 'text-[#71717A]'}`}>
                                        {profile?.auto_apply_enabled ? 'Enabled' : 'Disabled'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right: Form Fields */}
                    <div className="lg:col-span-2 space-y-4">
                        <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-5">
                            <h3 className="text-sm font-semibold text-white mb-4">Personal Information</h3>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Full Name</label>
                                    <input
                                        name="full_name"
                                        defaultValue={profile?.full_name}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="John Doe"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Current Title</label>
                                    <input
                                        name="current_title"
                                        defaultValue={profile?.current_title}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="Software Engineer"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                        <Mail size={10} className="inline mr-1" />
                                        Email
                                    </label>
                                    <input
                                        name="email"
                                        type="email"
                                        defaultValue={profile?.email}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="john@example.com"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                        <Phone size={10} className="inline mr-1" />
                                        Phone
                                    </label>
                                    <input
                                        name="phone"
                                        defaultValue={profile?.phone}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="+33 6 12 34 56 78"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                        <Linkedin size={10} className="inline mr-1" />
                                        LinkedIn URL
                                    </label>
                                    <input
                                        name="linkedin_url"
                                        defaultValue={profile?.linkedin_url}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="https://linkedin.com/in/..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                        <Github size={10} className="inline mr-1" />
                                        GitHub URL
                                    </label>
                                    <input
                                        name="github_url"
                                        defaultValue={profile?.github_url}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="https://github.com/..."
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                        <Globe size={10} className="inline mr-1" />
                                        Portfolio URL
                                    </label>
                                    <input
                                        name="portfolio_url"
                                        defaultValue={profile?.portfolio_url}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="https://portfolio.com"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Location</label>
                                    <input
                                        name="location"
                                        defaultValue={profile?.location}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="Paris, France"
                                    />
                                </div>
                            </div>

                            <div className="mt-4">
                                <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Skills (comma separated)</label>
                                <input
                                    name="skills"
                                    defaultValue={profile?.skills?.join(', ')}
                                    className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                    placeholder="Python, React, Machine Learning, ..."
                                />
                            </div>
                        </div>

                        {/* Save Button */}
                        <div className="flex items-center gap-4">
                            <button
                                type="submit"
                                disabled={saveMutation.isPending}
                                className="inline-flex items-center gap-2 bg-gradient-to-r from-[#FF6B35] to-[#F7931E] text-white px-6 py-2.5 rounded-xl font-semibold text-sm hover:opacity-90 transition-all shadow-lg shadow-[#FF6B35]/20"
                            >
                                <Save size={16} />
                                {saveMutation.isPending ? 'Saving...' : 'Save Profile'}
                            </button>

                            {isSuccess && (
                                <span className="flex items-center gap-2 text-[#22C55E] text-sm">
                                    <CheckCircle2 size={16} />
                                    Profile saved!
                                </span>
                            )}
                        </div>
                    </div>
                </form>
            )}

            {/* Auto-Apply Tab */}
            {activeTab === 'autoapply' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Status Card */}
                    <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                <Zap size={20} className="text-[#FF6B35]" />
                                Auto-Apply Status
                            </h3>

                            <button
                                onClick={() => toggleAutoApply.mutate(!profile?.auto_apply_enabled)}
                                disabled={!autoApplyStatus?.ready}
                                className={`relative w-14 h-7 rounded-full transition-colors ${profile?.auto_apply_enabled ? 'bg-[#22C55E]' : 'bg-[#3F3F46]'
                                    } ${!autoApplyStatus?.ready ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                            >
                                <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-all ${profile?.auto_apply_enabled ? 'left-8' : 'left-1'
                                    }`} />
                            </button>
                        </div>

                        {autoApplyStatus?.ready ? (
                            <div className="flex items-center gap-3 p-4 bg-[#22C55E]/10 rounded-lg border border-[#22C55E]/20">
                                <CheckCircle2 size={24} className="text-[#22C55E]" />
                                <div>
                                    <p className="font-medium text-[#22C55E]">Ready to auto-apply!</p>
                                    <p className="text-sm text-[#71717A]">When you like a job, we'll send your CV automatically.</p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                <div className="flex items-start gap-3 p-4 bg-[#F59E0B]/10 rounded-lg border border-[#F59E0B]/20">
                                    <AlertCircle size={24} className="text-[#F59E0B] shrink-0" />
                                    <div>
                                        <p className="font-medium text-[#F59E0B]">Setup Required</p>
                                        <p className="text-sm text-[#71717A]">Complete the following to enable auto-apply:</p>
                                    </div>
                                </div>

                                <ul className="space-y-2">
                                    {autoApplyStatus?.issues?.map((issue: string, i: number) => (
                                        <li key={i} className="flex items-center gap-2 text-sm text-[#EF4444]">
                                            <X size={14} />
                                            {issue}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    {/* SMTP Configuration */}
                    <div className="bg-[#1A1A1D] rounded-xl border border-white/5 p-6">
                        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                            <Shield size={20} className="text-[#8B5CF6]" />
                            Email Configuration (SMTP)
                        </h3>

                        <p className="text-sm text-[#71717A] mb-4">
                            Configure your email settings to send applications automatically.
                        </p>

                        <form onSubmit={(e) => {
                            e.preventDefault()
                            const formData = new FormData(e.currentTarget)
                            const data: Record<string, any> = {}
                            formData.forEach((value, key) => { if (value) data[key] = value })
                            saveMutation.mutate(data)
                        }} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">SMTP Host</label>
                                    <input
                                        name="smtp_host"
                                        defaultValue={profile?.smtp_host}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="smtp.gmail.com"
                                    />
                                </div>
                                <div>
                                    <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">SMTP Port</label>
                                    <input
                                        name="smtp_port"
                                        type="number"
                                        defaultValue={profile?.smtp_port || 587}
                                        className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                        placeholder="587"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">SMTP Username (Email)</label>
                                <input
                                    name="smtp_user"
                                    defaultValue={profile?.smtp_user}
                                    className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                    placeholder="your.email@gmail.com"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">
                                    SMTP Password / App Password
                                    {profile?.has_smtp_password && <Check size={12} className="inline ml-2 text-[#22C55E]" />}
                                </label>
                                <input
                                    name="smtp_password"
                                    type="password"
                                    placeholder={profile?.has_smtp_password ? "••••••••••••" : "Enter password"}
                                    className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm"
                                />
                                <p className="text-[10px] text-[#52525B] mt-1">For Gmail, use an App Password (2FA required)</p>
                            </div>

                            <button
                                type="submit"
                                disabled={saveMutation.isPending}
                                className="w-full bg-[#222226] text-white py-2.5 rounded-lg font-semibold text-sm hover:bg-[#2A2A2E] transition-all border border-white/10"
                            >
                                Save Email Settings
                            </button>
                        </form>
                    </div>

                    {/* Cover Letter Template */}
                    <div className="lg:col-span-2 bg-[#1A1A1D] rounded-xl border border-white/5 p-6">
                        <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                            <FileText size={20} className="text-[#3B82F6]" />
                            Cover Letter Template
                        </h3>

                        <p className="text-sm text-[#71717A] mb-4">
                            Customize your cover letter. Use placeholders: <code className="text-[#FF6B35]">{'{job_title}'}</code>, <code className="text-[#FF6B35]">{'{company}'}</code>, <code className="text-[#FF6B35]">{'{full_name}'}</code>, <code className="text-[#FF6B35]">{'{email}'}</code>
                        </p>

                        <form onSubmit={(e) => {
                            e.preventDefault()
                            const formData = new FormData(e.currentTarget)
                            saveMutation.mutate({
                                cover_letter_template: formData.get('cover_letter_template'),
                                custom_intro: formData.get('custom_intro'),
                            })
                        }} className="space-y-4">
                            <div>
                                <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Custom Introduction</label>
                                <textarea
                                    name="custom_intro"
                                    defaultValue={profile?.custom_intro}
                                    className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-3 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm h-20 resize-none"
                                    placeholder="A brief introduction about yourself..."
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-semibold text-[#52525B] uppercase tracking-wider mb-2">Full Template</label>
                                <textarea
                                    name="cover_letter_template"
                                    defaultValue={profile?.cover_letter_template}
                                    className="w-full bg-[#222226] border border-white/10 rounded-lg px-4 py-3 text-white placeholder-[#52525B] focus:border-[#FF6B35] outline-none text-sm h-48 resize-none font-mono text-xs"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={saveMutation.isPending}
                                className="bg-[#222226] text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-[#2A2A2E] transition-all border border-white/10"
                            >
                                Save Template
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Applications History Tab */}
            {activeTab === 'history' && (
                <div className="bg-[#1A1A1D] rounded-xl border border-white/5 overflow-hidden">
                    <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
                        <h3 className="font-semibold text-white">Application History</h3>
                        <span className="text-sm text-[#71717A]">{applications?.total_sent || 0} sent</span>
                    </div>

                    {applications?.recent?.length > 0 ? (
                        <div className="divide-y divide-white/5">
                            {applications.recent.map((app: any, i: number) => (
                                <div key={i} className="flex items-center gap-4 px-5 py-4 hover:bg-white/[0.02]">
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${app.status === 'sent' ? 'bg-[#22C55E]/10 text-[#22C55E]' :
                                            app.status === 'action_required' ? 'bg-[#F59E0B]/10 text-[#F59E0B]' :
                                                'bg-[#EF4444]/10 text-[#EF4444]'
                                        }`}>
                                        {app.status === 'sent' ? <Check size={20} /> :
                                            app.status === 'action_required' ? <ExternalLink size={20} /> :
                                                <X size={20} />}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-white truncate">{app.job_title}</p>
                                        <p className="text-sm text-[#71717A]">{app.company}</p>
                                    </div>

                                    <div className="text-right shrink-0">
                                        <span className={`inline-block px-2 py-1 rounded text-[10px] font-semibold uppercase ${app.status === 'sent' ? 'bg-[#22C55E]/10 text-[#22C55E]' :
                                                app.status === 'action_required' ? 'bg-[#F59E0B]/10 text-[#F59E0B]' :
                                                    'bg-[#52525B]/20 text-[#71717A]'
                                            }`}>
                                            {app.status === 'sent' ? 'Email Sent' :
                                                app.status === 'action_required' ? 'Manual Apply' :
                                                    app.status}
                                        </span>
                                        <p className="text-[10px] text-[#52525B] mt-1 flex items-center justify-end gap-1">
                                            <Clock size={10} />
                                            {new Date(app.applied_at).toLocaleDateString()}
                                        </p>
                                    </div>

                                    {app.url && (
                                        <a
                                            href={app.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="w-8 h-8 rounded-lg bg-[#222226] flex items-center justify-center text-[#71717A] hover:text-white hover:bg-[#FF6B35] transition-all"
                                        >
                                            <ExternalLink size={14} />
                                        </a>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="px-5 py-12 text-center">
                            <Send size={32} className="mx-auto mb-3 text-[#3F3F46]" />
                            <p className="text-sm text-[#52525B]">No applications yet.</p>
                            <p className="text-xs text-[#3F3F46] mt-1">Like jobs to start applying automatically!</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default ProfilePage