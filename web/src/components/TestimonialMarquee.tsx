'use client'

import { TestimonialCard } from './TestimonialCard'

const testimonials = [
  {
    name: "Sarah Chen",
    quote: "LookSmith helped me showcase my 3D sculptures to clients worldwide. The platform is intuitive and professional.",
    company: "Digital Art Studio",
    initials: "SC"
  },
  {
    name: "Marcus Rodriguez",
    quote: "As a freelance 3D artist, LookSmith gave me the visibility I needed to grow my business exponentially.",
    company: "Creative Solutions Inc",
    initials: "MR"
  },
  {
    name: "Emma Thompson",
    quote: "The quality of 3D artists on LookSmith is outstanding. Found the perfect designer for my project.",
    company: "Tech Startup",
    initials: "ET"
  },
  {
    name: "David Kim",
    quote: "LookSmith's platform made it easy to connect with clients and showcase my architectural visualizations.",
    company: "Architecture Firm",
    initials: "DK"
  },
  {
    name: "Lisa Wang",
    quote: "The 3D gallery feature is amazing. Clients can interact with my models before hiring me.",
    company: "Product Design Co",
    initials: "LW"
  },
  {
    name: "James Wilson",
    quote: "LookSmith transformed how I present my 3D work. The professional presentation helped me land major clients.",
    company: "Game Studio",
    initials: "JW"
  },
  {
    name: "Maria Garcia",
    quote: "The platform's ease of use and professional appearance helped me establish credibility in the 3D art space.",
    company: "Animation Studio",
    initials: "MG"
  },
  {
    name: "Alex Johnson",
    quote: "LookSmith provided the perfect platform to showcase my 3D jewelry designs to a global audience.",
    company: "Jewelry Design",
    initials: "AJ"
  },
  {
    name: "Sophie Brown",
    quote: "The interactive 3D viewer feature is incredible. Clients love being able to explore my designs in detail.",
    company: "Interior Design",
    initials: "SB"
  },
  {
    name: "Ryan Davis",
    quote: "LookSmith helped me transition from traditional art to 3D modeling. The community support is fantastic.",
    company: "Art Collective",
    initials: "RD"
  }
]

export function TestimonialMarquee() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground mb-4">
            Trusted by Creators Worldwide
          </h2>
          <p className="text-lg text-muted-foreground">
            Join thousands of 3D artists and clients who are already using LookSmith
          </p>
        </div>

        {/* Top Row - Moving Left */}
        <div className="overflow-hidden mb-8">
          <div className="flex animate-marquee-left">
            {testimonials.map((testimonial, index) => (
              <TestimonialCard key={`top-${index}`} {...testimonial} />
            ))}
            {/* Duplicate for seamless loop */}
            {testimonials.map((testimonial, index) => (
              <TestimonialCard key={`top-dup-${index}`} {...testimonial} />
            ))}
          </div>
        </div>

        {/* Bottom Row - Moving Right */}
        <div className="overflow-hidden">
          <div className="flex animate-marquee-right">
            {testimonials.map((testimonial, index) => (
              <TestimonialCard key={`bottom-${index}`} {...testimonial} />
            ))}
            {/* Duplicate for seamless loop */}
            {testimonials.map((testimonial, index) => (
              <TestimonialCard key={`bottom-dup-${index}`} {...testimonial} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
