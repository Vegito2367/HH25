'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Request } from '@/types/database'
import { User } from '@supabase/supabase-js'
import { Plus, DollarSign, Calendar, User as UserIcon, FileText } from 'lucide-react'
import LookSmithNavbar from '@/components/LookSmithNavbar'

export default function RequestsPage() {
  const [requests, setRequests] = useState<Request[]>([])
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    budget: ''
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setUser(session?.user || null)
    }
    getUser()
    fetchRequests()
  }, [])

  const fetchRequests = async () => {
    try {
      const { data, error } = await supabase
        .from('requests')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) throw error
      setRequests(data || [])
    } catch (error) {
      console.error('Error fetching requests:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setSuccess('')

    try {
      if (!user) throw new Error('User not authenticated')

      const { error } = await supabase
        .from('requests')
        .insert({
          title: formData.title,
          description: formData.description,
          budget: parseFloat(formData.budget),
          buyer_name: user.user_metadata?.name || user.email?.split('@')[0] || 'Anonymous',
          buyer_id: user.id
        })

      if (error) throw error

      setSuccess('Request posted successfully!')
      setFormData({ title: '', description: '', budget: '' })
      setShowForm(false)
      fetchRequests()
    } catch (error: any) {
      setError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <LookSmithNavbar />
        <div className="pt-16 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="animate-pulse">
            <div className="h-8 bg-gray-300 rounded w-1/4 mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-lg shadow-md p-6">
                  <div className="h-6 bg-gray-300 rounded mb-4"></div>
                  <div className="h-4 bg-gray-300 rounded mb-2"></div>
                  <div className="h-4 bg-gray-300 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <LookSmithNavbar />
      <div className="pt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Job Requests</h1>
            <p className="text-gray-600">Find projects that match your skills</p>
          </div>
          {user && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors flex items-center"
            >
              <Plus className="h-5 w-5 mr-2" />
              Post Request
            </button>
          )}
        </div>

        {/* Post Request Form */}
        {showForm && user && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Post a New Request</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                  Request Title *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <FileText className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    id="title"
                    name="title"
                    required
                    value={formData.title}
                    onChange={handleInputChange}
                    className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                    placeholder="e.g., Need a website for my business"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description *
                </label>
                <textarea
                  id="description"
                  name="description"
                  required
                  rows={4}
                  value={formData.description}
                  onChange={handleInputChange}
                  className="block w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                  placeholder="Describe your project requirements..."
                />
              </div>

              <div>
                <label htmlFor="budget" className="block text-sm font-medium text-gray-700 mb-2">
                  Budget (USD) *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <DollarSign className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    type="number"
                    id="budget"
                    name="budget"
                    required
                    min="10"
                    step="0.01"
                    value={formData.budget}
                    onChange={handleInputChange}
                    className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                    placeholder="500.00"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
                  {error}
                </div>
              )}

              {success && (
                <div className="bg-primary/10 border border-primary/20 text-primary px-4 py-3 rounded-md text-sm">
                  {success}
                </div>
              )}

              <div className="flex justify-end space-x-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  {submitting ? 'Posting...' : 'Post Request'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Requests Grid */}
        {requests.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-500 text-lg mb-4">No requests found</div>
            <p className="text-gray-400">
              {user ? 'Be the first to post a request!' : 'Sign in to post a request'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {requests.map((request) => (
              <div key={request.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-semibold text-gray-900 line-clamp-2">
                    {request.title}
                  </h3>
                  <span className="text-2xl font-bold text-primary ml-2">
                    ${request.budget}
                  </span>
                </div>

                <p className="text-gray-600 mb-4 line-clamp-3">
                  {request.description}
                </p>

                <div className="flex items-center justify-between">
                  <div className="flex items-center text-sm text-gray-500">
                    <UserIcon className="h-4 w-4 mr-1" />
                    <span>{request.buyer_name}</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-500">
                    <Calendar className="h-4 w-4 mr-1" />
                    <span>{new Date(request.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="mt-4">
                  <button className="w-full bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
                    Apply for this Project
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </div>
  )
}

