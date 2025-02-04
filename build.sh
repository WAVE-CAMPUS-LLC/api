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

# Step 4: Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Step 5: Start the application server
echo "Starting the application server..."
gunicorn wave_v1.wsgi:application