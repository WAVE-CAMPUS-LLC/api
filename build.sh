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
npm run build



# Step 3: Collect static files for Django
echo "Collecting Django static files..."
python manage.py collectstatic --no-input

# Step 4: Ensure migrations are applied
echo "Applying Django migrations..."
python manage.py migrate --no-input

find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# Step 5: Clean up node_modules if exists
rm -rf node_modules

python manage.py runserver 0.0.0.0:$PORT

# Step 5: Output message for Vercel
echo "Setup complete. Ready for deployment on Vercel."