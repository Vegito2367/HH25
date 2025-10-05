'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function LookSmithNavbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="text-2xl font-bold text-primary">
              LookSmith
            </Link>
          </div>


          {/* CTA Buttons */}
          <div className="flex items-center space-x-4">
            <Button variant="ghost" asChild>
              <Link href="/login">Login</Link>
            </Button>
            <Button asChild>
              <Link href="/signup">Join up</Link>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  )
}
