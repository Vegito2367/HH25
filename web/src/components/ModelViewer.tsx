'use client'

import { useState } from 'react'

interface ModelViewerProps {
  glbUrl?: string
  imageUrl?: string
  className?: string
}

export default function ModelViewer({ glbUrl, imageUrl, className = "w-full h-64" }: ModelViewerProps) {
  const [isLoading, setIsLoading] = useState(false)

  if (!glbUrl) {
    // Fallback to image if no GLB file
    return (
      <div className={`${className} bg-gray-100 rounded-lg overflow-hidden`}>
        {imageUrl ? (
          <img 
            src={imageUrl} 
            alt="Listing preview" 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-2">📦</div>
              <div className="text-sm">No preview available</div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const handleViewModel = () => {
    setIsLoading(true)
    // Open GLB file in new tab
    window.open(glbUrl, '_blank')
    setTimeout(() => setIsLoading(false), 1000)
  }

  return (
    <div className={`${className} bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg overflow-hidden relative group cursor-pointer`} onClick={handleViewModel}>
      {/* 3D Model Preview Area */}
      <div className="w-full h-full flex flex-col items-center justify-center p-4">
        {/* 3D Icon with Animation */}
        <div className="text-6xl mb-4 transform group-hover:scale-110 transition-transform duration-300">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-full opacity-20 blur-lg"></div>
            <div className="relative text-blue-600">🎨</div>
          </div>
        </div>
        
        {/* Model Info */}
        <div className="text-center mb-4">
          <div className="text-lg font-semibold text-gray-700 mb-1">3D Model Ready</div>
          <div className="text-sm text-gray-500 mb-2">GLB File Available</div>
          <div className="text-xs text-gray-400 font-mono bg-white/50 px-2 py-1 rounded">
            {glbUrl.split('/').pop()}
          </div>
        </div>

        {/* Interactive Button */}
        <div className="relative">
          <div className="absolute inset-0 bg-blue-600 rounded-lg blur-sm opacity-50 group-hover:opacity-75 transition-opacity"></div>
          <button 
            className={`relative bg-blue-600 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-blue-700 transition-all duration-200 transform group-hover:scale-105 ${
              isLoading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Opening...
              </div>
            ) : (
              <div className="flex items-center">
                <span className="mr-2">👁️</span>
                View 3D Model
              </div>
            )}
          </button>
        </div>

        {/* Hover Effect */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        
        {/* Corner Badge */}
        <div className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full font-medium">
          3D
        </div>
      </div>
    </div>
  )
}
