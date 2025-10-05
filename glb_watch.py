# GLB File Watcher
# Watches for new .glb files and uploads them to Supabase Storage
# Uses SERVICE ROLE KEY to bypass RLS policies
#
# Dependencies:
# pip install watchdog supabase

import os
import time
import random
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from supabase import create_client, Client

# FILL THESE WITH YOUR SUPABASE PROJECT CREDENTIALS:
SUPABASE_URL = "https://oushklesskesjkjuoetu.supabase.co/"
# Use SERVICE ROLE KEY instead of ANON KEY to bypass RLS
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91c2hrbGVzc2tlc2pranVvZXR1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTYwNzAxOSwiZXhwIjoyMDc1MTgzMDE5fQ.P-PYf8oDnXFrUDGcGelvjPcJb2kfNAdGyr5r3_SRhkk"  # Get this from Supabase Dashboard > Settings > API

SELLER_ID = "03cc84fc-1b2c-48c6-854e-04ba05cc2cd9"
SELLER_NAME = "Zain"

FOLDER_TO_WATCH = "./output"
BUCKET_NAME = "3d-models"
TABLE_NAME = "listings"

# Use service role key to bypass RLS
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_random_title():
    adjectives = ["Amazing", "Stunning", "Epic", "Fantastic", "Incredible", "Beautiful", "Magnificent", "Spectacular", "Awesome", "Brilliant"]
    nouns = ["Model", "Creation", "Artwork", "Design", "Masterpiece", "Work", "Piece", "Asset", "Object", "Structure"]
    numbers = ["2024", "Pro", "Ultra", "Max", "Plus", "Elite", "Premium", "Advanced", "Modern", "Classic"]
    
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    number = random.choice(numbers)
    
    return f"{adjective} {noun} {number}"

def get_random_category():
    categories = ["3D Models", "Digital Art", "Game Assets", "Architecture", "Vehicles", "Characters", "Environment", "Props", "Weapons", "Furniture"]
    return random.choice(categories)

def get_random_description():
    starts = ["This is an", "A high-quality", "Professional", "Detailed", "Hand-crafted", "Premium", "Custom", "Unique", "Exclusive", "Limited edition"]
    middles = ["3D model", "digital asset", "game-ready model", "architectural piece", "character model", "environmental asset", "prop model", "vehicle model"]
    ends = ["ready for use in any project.", "perfect for game development.", "ideal for visualization projects.", "suitable for commercial use.", "optimized for real-time rendering.", "with detailed textures and materials.", "created with attention to detail.", "designed for professional workflows."]
    
    start = random.choice(starts)
    middle = random.choice(middles)
    end = random.choice(ends)
    
    return f"{start} {middle} {end}"

def get_random_price():
    # Generate random prices between $5 and $50
    base_price = random.uniform(5, 50)
    # Round to 2 decimal places
    return round(base_price, 2)

class GLBHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.glb'):
            return
        
        filename = os.path.basename(event.src_path)
        print(f"🎯 Detected new GLB file: {filename}")
        
        try:
            # Upload file to Supabase Storage
            print(f"📤 Uploading {filename} to Supabase Storage...")
            with open(event.src_path, "rb") as f:
                file_data = f.read()
            
            # Upload directly to bucket root first (simpler approach)
            storage_path = filename
            
            # Upload to storage bucket
            try:
                upload_result = supabase.storage.from_(BUCKET_NAME).upload(storage_path, file_data)
                print(f"✅ Upload successful!")
            except Exception as upload_error:
                print(f"❌ Upload failed: {upload_error}")
                return
            
            # Get public URL
            public_url_result = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
            glb_file_url = public_url_result
            
            print(f"✅ File uploaded successfully!")
            print(f"🔗 Public URL: {glb_file_url}")
            
            # Prepare listing data
            listing_data = {
                "title": get_random_title(),
                "description": get_random_description(),
                "price": get_random_price(),
                "category": get_random_category(),
                "image_url": "https://via.placeholder.com/150",
                "glb_file_url": glb_file_url,
                "seller_id": SELLER_ID,
                "seller_name": SELLER_NAME
            }
            
            # Insert into listings table
            print(f"📝 Creating listing in database...")
            try:
                insert_result = supabase.table(TABLE_NAME).insert(listing_data).execute()
                print(f"✅ Database insert successful!")
            except Exception as db_error:
                print(f"❌ Database insert failed: {db_error}")
                return
            
            print(f"🎉 SUCCESS! Listing created successfully!")
            print(f"📊 Listing Data:")
            print(f"   - Title: {listing_data['title']}")
            print(f"   - Category: {listing_data['category']}")
            print(f"   - Price: ${listing_data['price']}")
            print(f"   - GLB URL: {glb_file_url}")
            print(f"   - Seller: {SELLER_NAME} ({SELLER_ID})")
            print(f"   - Database ID: {insert_result.data[0]['id'] if insert_result.data and len(insert_result.data) > 0 else 'N/A'}")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            print("-" * 60)

def ensure_output_folder():
    """Create the output folder if it doesn't exist."""
    if not os.path.exists(FOLDER_TO_WATCH):
        os.makedirs(FOLDER_TO_WATCH)
        print(f"📁 Created output folder: {FOLDER_TO_WATCH}")

def test_supabase_connection():
    """Test the Supabase connection."""
    try:
        # Test storage bucket access
        bucket_list = supabase.storage.list_buckets()
        print(f"✅ Supabase connection successful!")
        print(f"📦 Available buckets: {[bucket.name for bucket in bucket_list]}")
        
        # Check if our bucket exists
        bucket_names = [bucket.name for bucket in bucket_list]
        if BUCKET_NAME not in bucket_names:
            print(f"⚠️  Warning: Bucket '{BUCKET_NAME}' not found!")
            print(f"   Available buckets: {bucket_names}")
            print(f"   Please create the '{BUCKET_NAME}' bucket in Supabase Storage")
        else:
            print(f"✅ Found bucket '{BUCKET_NAME}'!")
        
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 GLB File Watcher")
    print("=" * 60)
    
    # Check if service key is set
    if SUPABASE_SERVICE_KEY == "YOUR_SERVICE_ROLE_KEY_HERE":
        print("❌ Please set your SUPABASE_SERVICE_KEY!")
        print("💡 Get it from: Supabase Dashboard > Settings > API > service_role key")
        exit(1)
    
    # Test connection first
    if not test_supabase_connection():
        print("❌ Cannot proceed without Supabase connection. Please check your credentials.")
        exit(1)
    
    # Ensure output folder exists
    ensure_output_folder()
    
    print(f"👀 Watching for new .glb files in: {FOLDER_TO_WATCH}")
    print(f"📦 Uploading to bucket: {BUCKET_NAME} (root level)")
    print(f"📊 Inserting into table: {TABLE_NAME}")
    print(f"🔑 Using SERVICE ROLE KEY (bypasses RLS)")
    print("=" * 60)
    print("💡 To test: Copy a .glb file into the './output' folder")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    # Set up file watcher
    observer = Observer()
    observer.schedule(GLBHandler(), FOLDER_TO_WATCH, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping file watcher...")
        observer.stop()
    
    observer.join()
    print("👋 File watcher stopped. Goodbye!")
