set -e

echo "Starting Vercel deployment script..."

# Step 1: Install required Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Step 2: Build Tailwind CSS or any frontend assets
echo "Building frontend assets..."
npm run build



# Step 3: Collect static files for Django
echo "Collecting Django static files..."
python manage.py collectstatic --no-input

# Step 4: Ensure migrations are applied
echo "Applying Django migrations..."
python manage.py migrate --no-input

# Step 5: Output message for Vercel
echo "Setup complete. Ready for deployment on Vercel."