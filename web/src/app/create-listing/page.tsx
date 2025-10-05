'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { Upload, DollarSign, Tag, FileText, User as UserIcon, File } from 'lucide-react'

const categories = [
  '3D Models',
  'Web Development',
  'Graphic Design',
  'Writing & Translation',
  'Digital Marketing',
  'Video & Animation',
  'Music & Audio',
  'Programming & Tech',
  'Business',
  'Lifestyle',
  'Other'
]

export default function CreateListingPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: '',
    category: '',
    image_url: '',
    glb_file_url: ''
  })
  const [glbFile, setGlbFile] = useState<File | null>(null)
  const [uploadingFile, setUploadingFile] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const router = useRouter()

  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.user) {
        router.push('/auth')
        return
      }
      setUser(session.user)
      setLoading(false)
    }
    getUser()
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setSuccess('')

    try {
      if (!user) throw new Error('User not authenticated')

      const { error } = await supabase
        .from('listings')
        .insert({
          title: formData.title,
          description: formData.description,
          price: parseFloat(formData.price),
          category: formData.category,
          seller_name: user.user_metadata?.name || user.email?.split('@')[0] || 'Anonymous',
          seller_id: user.id,
          image_url: formData.image_url || null,
          glb_file_url: formData.glb_file_url || null
        })

      if (error) throw error

      setSuccess('Listing created successfully!')
      setTimeout(() => {
        router.push('/listings')
      }, 2000)
    } catch (error: any) {
      setError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleFileUpload = async (file: File) => {
    if (!user) return

    setUploadingFile(true)
    try {
      // Create a unique filename
      const fileExt = file.name.split('.').pop()
      const fileName = `${user.id}/${Date.now()}.${fileExt}`
      
      // Upload to Supabase Storage
      const { data, error } = await supabase.storage
        .from('3d-models')
        .upload(fileName, file)

      if (error) throw error

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from('3d-models')
        .getPublicUrl(fileName)

      setFormData(prev => ({
        ...prev,
        glb_file_url: publicUrl
      }))
    } catch (error: any) {
      setError(`File upload failed: ${error.message}`)
    } finally {
      setUploadingFile(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      if (!file.name.toLowerCase().endsWith('.glb')) {
        setError('Please upload a GLB file (.glb)')
        return
      }
      
      // Validate file size (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        setError('File size must be less than 50MB')
        return
      }

      setGlbFile(file)
      handleFileUpload(file)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Listing</h1>
          <p className="text-gray-600">Share your skills and start earning</p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Title */}
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                Service Title *
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
                  placeholder="e.g., Professional Logo Design"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                Service Description *
              </label>
              <textarea
                id="description"
                name="description"
                required
                rows={6}
                value={formData.description}
                onChange={handleInputChange}
                className="block w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                placeholder="Describe what you offer, your experience, and what clients can expect..."
              />
            </div>

            {/* Price and Category Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Price */}
              <div>
                <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-2">
                  Price (USD) *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <DollarSign className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    type="number"
                    id="price"
                    name="price"
                    required
                    min="5"
                    step="0.01"
                    value={formData.price}
                    onChange={handleInputChange}
                    className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                    placeholder="25.00"
                  />
                </div>
              </div>

              {/* Category */}
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                  Category *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Tag className="h-5 w-5 text-gray-400" />
                  </div>
                  <select
                    id="category"
                    name="category"
                    required
                    value={formData.category}
                    onChange={handleInputChange}
                    className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                  >
                    <option value="">Select a category</option>
                    {categories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* GLB File Upload */}
            <div>
              <label htmlFor="glb_file" className="block text-sm font-medium text-gray-700 mb-2">
                3D Model File (GLB) - Optional
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <File className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="file"
                  id="glb_file"
                  name="glb_file"
                  accept=".glb"
                  onChange={handleFileChange}
                  disabled={uploadingFile}
                  className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring disabled:opacity-50"
                />
              </div>
              <p className="mt-1 text-sm text-gray-500">
                Upload a GLB file to showcase your 3D model (max 50MB)
              </p>
              {glbFile && (
                <div className="mt-2 p-2 bg-primary/10 border border-primary/20 rounded-md">
                  <p className="text-sm text-primary">
                    ✓ File uploaded: {glbFile.name}
                  </p>
                </div>
              )}
              {uploadingFile && (
                <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-600">
                    Uploading file...
                  </p>
                </div>
              )}
            </div>

            {/* Image URL */}
            <div>
              <label htmlFor="image_url" className="block text-sm font-medium text-gray-700 mb-2">
                Preview Image URL (Optional)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Upload className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="url"
                  id="image_url"
                  name="image_url"
                  value={formData.image_url}
                  onChange={handleInputChange}
                  className="block w-full pl-10 pr-3 py-2 border border-input rounded-md focus:outline-none focus:ring-ring focus:border-ring"
                  placeholder="https://example.com/image.jpg"
                />
              </div>
              <p className="mt-1 text-sm text-gray-500">
                Add a preview image URL to make your listing more attractive
              </p>
            </div>

            {/* Seller Info */}
            <div className="bg-gray-50 p-4 rounded-md">
              <div className="flex items-center">
                <UserIcon className="h-5 w-5 text-gray-400 mr-2" />
                <span className="text-sm text-gray-600">
                  Listing will be created under: <strong>{user?.user_metadata?.name || user?.email?.split('@')[0] || 'Anonymous'}</strong>
                </span>
              </div>
            </div>

            {/* Error/Success Messages */}
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

            {/* Submit Button */}
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={() => router.back()}
                className="px-6 py-2 border border-input rounded-md text-muted-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Creating...' : 'Create Listing'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

