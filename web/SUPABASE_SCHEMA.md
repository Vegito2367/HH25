# Supabase Database Schema

## Tables

### 1. listings
```sql
CREATE TABLE listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  category TEXT NOT NULL,
  seller_name TEXT NOT NULL,
  seller_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  image_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE listings ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read listings
CREATE POLICY "Anyone can read listings" ON listings
  FOR SELECT USING (true);

-- Policy: Authenticated users can insert their own listings
CREATE POLICY "Users can insert their own listings" ON listings
  FOR INSERT WITH CHECK (auth.uid() = seller_id);

-- Policy: Users can update their own listings
CREATE POLICY "Users can update their own listings" ON listings
  FOR UPDATE USING (auth.uid() = seller_id);

-- Policy: Users can delete their own listings
CREATE POLICY "Users can delete their own listings" ON listings
  FOR DELETE USING (auth.uid() = seller_id);
```

### 2. requests
```sql
CREATE TABLE requests (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  budget DECIMAL(10,2) NOT NULL,
  buyer_name TEXT NOT NULL,
  buyer_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE requests ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can read requests
CREATE POLICY "Anyone can read requests" ON requests
  FOR SELECT USING (true);

-- Policy: Authenticated users can insert their own requests
CREATE POLICY "Users can insert their own requests" ON requests
  FOR INSERT WITH CHECK (auth.uid() = buyer_id);

-- Policy: Users can update their own requests
CREATE POLICY "Users can update their own requests" ON requests
  FOR UPDATE USING (auth.uid() = buyer_id);

-- Policy: Users can delete their own requests
CREATE POLICY "Users can delete their own requests" ON requests
  FOR DELETE USING (auth.uid() = buyer_id);
```

## Setup Instructions

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Run the above SQL commands to create the tables and policies
4. Update your `.env.local` file with your Supabase URL and anon key

## Categories for Listings

Suggested categories:
- Web Development
- Graphic Design
- Writing & Translation
- Digital Marketing
- Video & Animation
- Music & Audio
- Programming & Tech
- Business
- Lifestyle
- Other

