set -e

echo "Starting Vercel deployment script..."

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 1: Install required Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Step 2: Build Tailwind CSS or any frontend assets
echo "Building frontend assets..."
npm run build:prod



# Step 3: Collect static files for Django
echo "Collecting Django static files..."
python manage.py collectstatic --no-input


# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

# Step 5: Output message for Vercel
echo "Setup complete. Ready for deployment on Vercel."