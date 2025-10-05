'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { LogOut, User as UserIcon } from 'lucide-react'

export default function Navbar() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Get initial session
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setUser(session?.user ?? null)
      setLoading(false)
    }

    getSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setUser(session?.user ?? null)
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-2xl font-bold text-primary">
                FindSmith
              </Link>
            </div>
          </div>
        </div>
      </nav>
    )
  }

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="text-2xl font-bold text-primary">
              FindSmith
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link
                  href="/listings"
                  className="text-muted-foreground hover:text-primary px-3 py-2 rounded-md text-sm font-medium"
                >
                  Listings
                </Link>
                <Link
                  href="/create-listing"
                  className="text-muted-foreground hover:text-primary px-3 py-2 rounded-md text-sm font-medium"
                >
                  Create Listing
                </Link>
                <Link
                  href="/requests"
                  className="text-muted-foreground hover:text-primary px-3 py-2 rounded-md text-sm font-medium"
                >
                  Requests
                </Link>
                <div className="flex items-center space-x-2">
                  <UserIcon className="h-5 w-5 text-gray-500" />
                  <span className="text-sm text-gray-700">
                    {user.email}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 text-gray-700 hover:text-red-600 px-3 py-2 rounded-md text-sm font-medium"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/auth"
                  className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/90"
                >
                  Sign In
                </Link>
                <Link
                  href="/auth"
                  className="border border-primary text-primary px-4 py-2 rounded-md text-sm font-medium hover:bg-primary/10"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

