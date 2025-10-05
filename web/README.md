# WebApp - Fiverr-style Marketplace

A modern, full-stack web application built with Next.js, TypeScript, TailwindCSS, and Supabase. This is a Fiverr-style marketplace where freelancers can offer services and clients can post job requests.

## 🚀 Features

- **Landing Page**: Beautiful hero section with sample listings and call-to-action
- **Authentication**: Email/password and Google OAuth with Supabase Auth
- **Listings**: Browse, search, and filter service listings
- **Create Listings**: Freelancers can create and manage their service offerings
- **Job Requests**: Clients can post project requests with budgets
- **Responsive Design**: Mobile-first design that works on all devices
- **Real-time Updates**: Live data synchronization with Supabase

## 🛠 Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript
- **Styling**: TailwindCSS
- **Backend**: Supabase (PostgreSQL, Auth, Real-time)
- **Icons**: Lucide React
- **Deployment**: Vercel (recommended)

## 📋 Prerequisites

- Node.js 18+ 
- npm or yarn
- Supabase account

## 🚀 Quick Start

### 1. Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd web

# Install dependencies
npm install
```

### 2. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a new project
2. In your Supabase dashboard, go to **SQL Editor**
3. Run the following SQL commands to create the database schema:

```sql
-- Create listings table
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

-- Create policies for listings
CREATE POLICY "Anyone can read listings" ON listings
  FOR SELECT USING (true);

CREATE POLICY "Users can insert their own listings" ON listings
  FOR INSERT WITH CHECK (auth.uid() = seller_id);

CREATE POLICY "Users can update their own listings" ON listings
  FOR UPDATE USING (auth.uid() = seller_id);

CREATE POLICY "Users can delete their own listings" ON listings
  FOR DELETE USING (auth.uid() = seller_id);

-- Create requests table
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

-- Create policies for requests
CREATE POLICY "Anyone can read requests" ON requests
  FOR SELECT USING (true);

CREATE POLICY "Users can insert their own requests" ON requests
  FOR INSERT WITH CHECK (auth.uid() = buyer_id);

CREATE POLICY "Users can update their own requests" ON requests
  FOR UPDATE USING (auth.uid() = buyer_id);

CREATE POLICY "Users can delete their own requests" ON requests
  FOR DELETE USING (auth.uid() = buyer_id);
```

4. Go to **Settings** > **API** in your Supabase dashboard
5. Copy your **Project URL** and **anon public** key

### 3. Environment Setup

1. Copy the example environment file:
```bash
cp env.local.example .env.local
```

2. Update `.env.local` with your Supabase credentials:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 4. Run the Application

```bash
# Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── auth/              # Authentication page
│   ├── listings/          # Browse services
│   ├── create-listing/    # Create new service
│   ├── requests/          # Job requests
│   ├── layout.tsx         # Root layout with navbar
│   └── page.tsx           # Landing page
├── components/            # Reusable components
│   └── Navbar.tsx         # Navigation component
├── lib/                   # Utility functions
│   └── supabase.ts        # Supabase client
└── types/                 # TypeScript definitions
    └── database.ts        # Database types
```

## 🎨 Pages Overview

### Landing Page (`/`)
- Hero section with call-to-action
- Features showcase
- Sample service listings
- Responsive design

### Authentication (`/auth`)
- Email/password sign in/up
- Google OAuth integration
- Form validation and error handling

### Listings (`/listings`)
- Browse all service listings
- Search and filter functionality
- Category filtering
- Price sorting

### Create Listing (`/create-listing`)
- Form to create new service listings
- Image upload support
- Category selection
- Price setting

### Requests (`/requests`)
- View job requests from clients
- Post new project requests
- Budget and description fields

## 🔧 Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
```

## 🚀 Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy!

### Other Platforms

The app can be deployed to any platform that supports Next.js:
- Netlify
- Railway
- DigitalOcean App Platform
- AWS Amplify

## 🔐 Security Features

- Row Level Security (RLS) enabled on all tables
- User authentication required for creating content
- Users can only edit/delete their own listings/requests
- Secure environment variable handling

## 🎯 Future Enhancements

- [ ] Real-time messaging between buyers and sellers
- [ ] Payment integration (Stripe)
- [ ] Rating and review system
- [ ] File upload for portfolios
- [ ] Advanced search filters
- [ ] Email notifications
- [ ] Admin dashboard
- [ ] Mobile app (React Native)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:

1. Check the [Issues](https://github.com/your-username/web/issues) page
2. Create a new issue with detailed information
3. Make sure your Supabase setup is correct
4. Verify your environment variables

## 🙏 Acknowledgments

- [Next.js](https://nextjs.org/) for the amazing React framework
- [Supabase](https://supabase.com/) for the backend infrastructure
- [TailwindCSS](https://tailwindcss.com/) for the utility-first CSS
- [Lucide](https://lucide.dev/) for the beautiful icons