'use client'

import { useState, useEffect } from 'react'

interface ModelViewerProps {
  glbUrl?: string
  imageUrl?: string
  className?: string
}

export default function ModelViewer({ glbUrl, imageUrl, className = "w-full h-64" }: ModelViewerProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    // Load model-viewer script if not already loaded
    if (glbUrl && typeof window !== 'undefined') {
      const script = document.createElement('script')
      script.type = 'module'
      script.src = 'https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js'
      script.onload = () => setIsLoading(false)
      script.onerror = () => setHasError(true)
      
      // Check if script is already loaded
      if (!document.querySelector('script[src*="model-viewer"]')) {
        document.head.appendChild(script)
      } else {
        setIsLoading(false)
      }
    }
  }, [glbUrl])

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

  if (hasError) {
    return (
      <div className={`${className} bg-red-50 rounded-lg overflow-hidden flex items-center justify-center`}>
        <div className="text-center p-4">
          <div className="text-red-500 text-4xl mb-2">⚠️</div>
          <div className="text-sm text-red-700 mb-2">Failed to load 3D model</div>
          <button 
            onClick={() => setHasError(false)}
            className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`${className} bg-gray-100 rounded-lg overflow-hidden relative group`}>
      {isLoading ? (
        <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <div className="text-sm text-gray-600">Loading 3D Model...</div>
          </div>
        </div>
      ) : (
        <>
          <model-viewer
            src={glbUrl}
            alt="3D Model"
            auto-rotate
            camera-controls
            touch-action="pan-y"
            style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#f3f4f6'
            }}
            onError={() => setHasError(true)}
          />
          
          {/* 3D Badge */}
          <div className="absolute top-2 right-2 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full font-medium shadow-lg z-10">
            3D
          </div>
          
          {/* Interactive Hint */}
          <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10">
            Drag to rotate • Scroll to zoom
          </div>
        </>
      )}
    </div>
  )
}
