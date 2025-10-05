'use client'

import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { TestimonialMarquee } from '@/components/TestimonialMarquee'
import { gsap } from 'gsap'

export default function Home() {
  const statementRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (statementRef.current) {
      const chars = statementRef.current.querySelectorAll('.char')
      
      // Set initial state - characters start below their position
      gsap.set(chars, { y: 50, opacity: 0 })
      
      // Animate characters with stagger
      gsap.to(chars, {
        y: 0,
        opacity: 1,
        duration: 0.6,
        ease: "back.out(1.7)",
        stagger: 0.03,
        delay: 0.5
      })
    }
  }, [])

  const statement = "The premier platform for 3D artists to showcase their work and connect with clients worldwide."
  const words = statement.split(' ')

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative h-screen flex items-end justify-start overflow-hidden">
        {/* 3D Background Element Placeholder */}
        <div className="absolute inset-0 z-0 bg-gradient-to-br from-primary/5 via-background to-secondary/5">
          {/* This div is designated for 3D elements - will sit behind everything */}
          <div className="absolute inset-0 opacity-20">
            {/* Placeholder for 3D scene */}
            <div className="absolute top-1/2 right-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl"></div>
            <div className="absolute bottom-1/4 left-1/3 w-64 h-64 bg-secondary/10 rounded-full blur-2xl"></div>
          </div>
        </div>

        {/* Hero Content */}
        <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
          <div className="max-w-3xl mx-auto text-center">
            <div ref={statementRef} className="text-xl md:text-2xl text-muted-foreground mb-12 max-w-2xl mx-auto">
              {words.map((word, wordIndex) => (
                <div key={wordIndex} className="inline-block overflow-hidden">
                  {word.split('').map((char, charIndex) => (
                    <span key={charIndex} className="char inline-block">
                      {char}
                    </span>
                  ))}
                  {wordIndex < words.length - 1 && <span className="char inline-block">&nbsp;</span>}
                </div>
              ))}
            </div>
            <Button size="lg" className="text-lg px-8 py-4 h-auto">
              Try it out
            </Button>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <TestimonialMarquee />
    </div>
  )
}
