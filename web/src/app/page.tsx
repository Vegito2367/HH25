'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { TestimonialMarquee } from '@/components/TestimonialMarquee'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

// Register ScrollTrigger plugin
gsap.registerPlugin(ScrollTrigger)
import { supabase } from '@/lib/supabase'
import { Listing } from '@/types/database'
import { Star } from 'lucide-react'
import ModelViewer from '@/components/ModelViewer'
import LookSmithNavbar from '@/components/LookSmithNavbar'

export default function Home() {
  const statementRef = useRef<HTMLDivElement>(null)
  const navbarRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const buttonRef = useRef<HTMLDivElement>(null)
  const [featuredListings, setFeaturedListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Set initial states - all elements start hidden
    gsap.set(navbarRef.current, { y: -100, opacity: 0 })
    gsap.set(videoRef.current, { scale: 1.1, opacity: 0 })
    gsap.set(buttonRef.current, { y: 50, opacity: 0 })
    
    if (statementRef.current) {
      const chars = statementRef.current.querySelectorAll('.char')
      gsap.set(chars, { y: 50, opacity: 0 })
    }
    
    // Set initial state for explanation cards
    gsap.set('.explanation-card', { x: -100, opacity: 0 })
    
    // Animate elements in sequence with a small delay
    const tl = gsap.timeline({ delay: 0.2 })
    
    // 1. Top bar animates in first
    tl.to(navbarRef.current, {
      y: 0,
      opacity: 1,
      duration: 0.8,
      ease: "power3.out"
    })
    
    // 2. Video animates in
    .to(videoRef.current, {
      scale: 1,
      opacity: 0.6,
      duration: 1.2,
      ease: "power2.out"
    }, "-=0.4")
    
    // 3. Statement animates in
    .to(statementRef.current?.querySelectorAll('.char') || [], {
      y: 0,
      opacity: 1,
      duration: 0.6,
      ease: "back.out(1.7)",
      stagger: 0.03
    }, "-=0.6")
    
    // 4. Button animates in last
    .to(buttonRef.current, {
      y: 0,
      opacity: 1,
      duration: 0.6,
      ease: "back.out(1.7)"
    }, "-=0.3")
    
    // 5. Animate explanation cards from left to right
    .to('.explanation-card', {
      x: 0,
      opacity: 1,
      duration: 0.8,
      ease: "power2.out",
      stagger: 0.2
    }, "-=0.1")
    
    // Set up scroll-triggered animations for cards
    ScrollTrigger.create({
      trigger: '.explanation-card',
      start: 'top 80%',
      end: 'bottom 20%',
      onEnter: () => {
        gsap.to('.explanation-card', {
          x: 0,
          opacity: 1,
          duration: 0.8,
          ease: "power2.out",
          stagger: 0.2
        })
      },
      onLeave: () => {
        gsap.to('.explanation-card', {
          y: -20,
          duration: 0.3,
          ease: "power2.out"
        })
      },
      onEnterBack: () => {
        gsap.to('.explanation-card', {
          y: 0,
          duration: 0.3,
          ease: "power2.out"
        })
      },
      onLeaveBack: () => {
        gsap.to('.explanation-card', {
          x: -100,
          opacity: 0,
          duration: 0.5,
          ease: "power2.out"
        })
      }
    })
    
    fetchFeaturedListings()
  }, [])

  const fetchFeaturedListings = async () => {
    try {
      const { data, error } = await supabase
        .from('listings')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(6) // Show only 6 featured listings

      if (error) throw error
      setFeaturedListings(data || [])
    } catch (error) {
      console.error('Error fetching featured listings:', error)
    } finally {
      setLoading(false)
    }
  }

  const statement = "The premier platform for 3D artists to showcase their work and connect with clients worldwide."
  const words = statement.split(' ')

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <div ref={navbarRef}>
        <LookSmithNavbar />
      </div>

      {/* Hero Section */}
      <section className="relative h-[150vh] flex items-end justify-start overflow-hidden">
        {/* Video Background */}
        <div className="absolute inset-0 z-0">
          <video 
            ref={videoRef}
            className="w-full h-screen object-cover sticky top-0"
            autoPlay 
            muted 
            loop={false}
            onLoadedData={(e) => {
              // Start blur effect at 3.5 seconds, stop video at 4 seconds and add blue tint
              setTimeout(() => {
                // Add blur effect
                e.currentTarget.style.filter = 'blur(8px)'
                e.currentTarget.style.transition = 'filter 0.5s ease-out'
              }, 3500)
              
              setTimeout(() => {
                e.currentTarget.pause()
                // Add blue tint overlay
                const overlay = document.createElement('div')
                overlay.className = 'absolute inset-0 bg-blue-500/20 pointer-events-none transition-opacity duration-1000'
                overlay.style.opacity = '0'
                e.currentTarget.parentElement?.appendChild(overlay)
                
                // Animate blue tint in
                setTimeout(() => {
                  overlay.style.opacity = '1'
                }, 100)
              }, 4000)
            }}
          >
            <source src="/geometric.mp4" type="video/mp4" />
            Your browser does not support the video tag.
          </video>
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background/20 to-secondary/5"></div>
        </div>

        {/* Hero Content */}
        <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24" style={{marginTop: '120vh'}}>
          <div className="text-center">
            <div ref={statementRef} className="text-lg md:text-xl lg:text-2xl italic text-muted-foreground max-w-2xl mx-auto leading-tight mb-12" style={{lineHeight: '1.2'}}>
              {words.map((word, wordIndex) => (
                <div key={wordIndex} className="inline-block overflow-hidden mr-3">
                  {word.split('').map((char, charIndex) => (
                    <span key={charIndex} className="char inline-block">
                      {char}
                    </span>
                  ))}
                  {wordIndex < words.length - 1 && <span className="char inline-block">&nbsp;</span>}
                </div>
              ))}
            </div>

            {/* Button below statement */}
            <div ref={buttonRef}>
              <Button size="lg" className="text-lg px-8 py-4 h-auto">
                Try it out
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Explanation Section */}
      <section className="py-20 bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Discover, create, and connect with the world's most talented 3D artists
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Card 1 */}
            <div className="explanation-card group">
              <div className="bg-white rounded-xl shadow-lg p-8 h-full hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6 group-hover:bg-blue-200 transition-colors duration-300">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Discover</h3>
                <p className="text-gray-600 leading-relaxed">
                  Browse through thousands of stunning 3D models created by talented artists from around the world.
                </p>
              </div>
            </div>

            {/* Card 2 */}
            <div className="explanation-card group">
              <div className="bg-white rounded-xl shadow-lg p-8 h-full hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6 group-hover:bg-green-200 transition-colors duration-300">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Create</h3>
                <p className="text-gray-600 leading-relaxed">
                  Upload your own 3D models and showcase your creativity to potential clients and collaborators.
                </p>
              </div>
            </div>

            {/* Card 3 */}
            <div className="explanation-card group">
              <div className="bg-white rounded-xl shadow-lg p-8 h-full hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-6 group-hover:bg-purple-200 transition-colors duration-300">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Connect</h3>
                <p className="text-gray-600 leading-relaxed">
                  Connect with clients, collaborate with other artists, and build meaningful professional relationships.
                </p>
              </div>
            </div>

            {/* Card 4 */}
            <div className="explanation-card group">
              <div className="bg-white rounded-xl shadow-lg p-8 h-full hover:shadow-2xl transition-all duration-300 hover:-translate-y-2">
                <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mb-6 group-hover:bg-orange-200 transition-colors duration-300">
                  <svg className="w-8 h-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Earn</h3>
                <p className="text-gray-600 leading-relaxed">
                  Monetize your skills and turn your passion for 3D art into a sustainable income stream.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Listings Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Featured 3D Models</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Discover amazing 3D creations from talented artists around the world
            </p>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-lg shadow-md p-6 h-[500px] flex flex-col animate-pulse">
                  <div className="h-64 bg-gray-300 rounded mb-4"></div>
                  <div className="h-6 bg-gray-300 rounded mb-3"></div>
                  <div className="h-4 bg-gray-300 rounded mb-2"></div>
                  <div className="h-4 bg-gray-300 rounded w-3/4 mb-4"></div>
                  <div className="flex justify-between items-center mb-4">
                    <div className="h-6 bg-gray-300 rounded w-20"></div>
                    <div className="h-4 bg-gray-300 rounded w-16"></div>
                  </div>
                  <div className="flex justify-between items-center mt-auto">
                    <div className="h-4 bg-gray-300 rounded w-24"></div>
                    <div className="h-8 bg-gray-300 rounded w-24"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : featuredListings.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-500 text-lg mb-4">No listings available yet</div>
              <p className="text-gray-400">Be the first to showcase your 3D models!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {featuredListings.map((listing) => (
                <div key={listing.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 h-[500px] flex flex-col">
                  {/* 3D Model Preview */}
                  <div className="mb-4">
                    <ModelViewer 
                      glbUrl={listing.glb_file_url} 
                      imageUrl={listing.image_url}
                      className="w-full h-64"
                    />
                  </div>

                  {/* Title and Price */}
                  <div className="flex justify-between items-start mb-3">
                    <h3 className="text-xl font-semibold text-gray-900 line-clamp-2 flex-1">
                      {listing.title}
                    </h3>
                    <span className="text-2xl font-bold text-primary ml-2 flex-shrink-0">
                      ${listing.price}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-gray-600 mb-4 line-clamp-3 flex-1">
                    {listing.description}
                  </p>

                  {/* Category and Rating */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
                      {listing.category}
                    </span>
                    <div className="flex items-center">
                      <Star className="h-4 w-4 text-yellow-400 fill-current" />
                      <span className="ml-1 text-sm text-gray-600">4.8</span>
                      <span className="ml-2 text-sm text-gray-500">(24)</span>
                    </div>
                  </div>

                  {/* Seller and Contact Button */}
                  <div className="flex items-center justify-between mt-auto">
                    <span className="text-sm text-gray-500">by {listing.seller_name}</span>
                    <button className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90 transition-colors">
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* View All Button */}
          <div className="text-center mt-12">
            <Button size="lg" className="text-lg px-8 py-4 h-auto">
              View All Listings
            </Button>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <TestimonialMarquee />
    </div>
  )
}
