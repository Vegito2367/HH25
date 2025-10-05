export interface Listing {
  id: string
  title: string
  description: string
  price: number
  category: string
  seller_name: string
  seller_id: string
  image_url?: string
  glb_file_url?: string
  created_at: string
  updated_at: string
}

export interface Request {
  id: string
  title: string
  description: string
  budget: number
  buyer_name: string
  buyer_id: string
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  name?: string
  created_at: string
}

