'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

interface TestimonialCardProps {
  name: string
  quote: string
  company: string
  avatar?: string
  initials: string
}

export function TestimonialCard({ name, quote, company, avatar, initials }: TestimonialCardProps) {
  return (
    <Card className="min-w-[300px] mx-4">
      <CardContent className="p-6">
        <div className="flex items-start space-x-4">
          <Avatar className="h-12 w-12">
            <AvatarImage src={avatar} alt={name} />
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <blockquote className="text-sm text-muted-foreground mb-2">
              "{quote}"
            </blockquote>
            <div className="text-sm font-medium">{name}</div>
            <div className="text-xs text-muted-foreground">{company}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
