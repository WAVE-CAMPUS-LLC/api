#!/usr/bin/env python
"""
Example script for generating universal QR codes.

Usage:
    python scripts/generate_qr_example.py

This script demonstrates how to use the universal QR code generation utilities
and management command functionality.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wave_v1.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from accountManagementApp.utils import generate_universal_qr_code_for_user, bulk_generate_universal_qr_codes


def generate_qr_for_single_user(username):
    """Generate QR code for a single user by username."""
    try:
        user = CustomUser.objects.get(username=username)
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={}
        )
        
        if created:
            print(f"Created profile for user: {username}")
        
        success = generate_universal_qr_code_for_user(profile)
        
        if success:
            print(f"✓ Successfully generated QR code for {username}")
            print(f"  QR code UUID: {profile.universal_qr_code}")
            if profile.universal_qr_code_image:
                print(f"  QR code image: {profile.universal_qr_code_image.url}")
        else:
            print(f"✗ Failed to generate QR code for {username}")
            
    except CustomUser.DoesNotExist:
        print(f"✗ User '{username}' not found")
    except Exception as e:
        print(f"✗ Error generating QR for {username}: {e}")


def generate_qr_for_all_users():
    """Generate QR codes for all users who don't have them."""
    try:
        # Get all user profiles that don't have QR codes
        profiles_without_qr = UserProfile.objects.filter(
            universal_qr_code_image__isnull=True
        ).select_related('user')
        
        total_count = profiles_without_qr.count()
        
        if total_count == 0:
            print("✓ All users already have universal QR codes!")
            return
        
        print(f"Found {total_count} users without QR codes")
        
        # Generate QR codes in batches
        stats = bulk_generate_universal_qr_codes(profiles_without_qr, batch_size=10)
        
        print(f"\nBulk generation complete:")
        print(f"  Total processed: {stats['total_count']}")
        print(f"  Successful: {stats['success_count']}")
        print(f"  Errors: {stats['error_count']}")
        print(f"  Skipped: {stats['skipped_count']}")
        
    except Exception as e:
        print(f"✗ Error in bulk generation: {e}")


def show_user_qr_info(username):
    """Show QR code information for a specific user."""
    try:
        user = CustomUser.objects.get(username=username)
        profile = user.user_profile
        
        print(f"\nQR Code info for {username}:")
        print(f"  Has QR code: {'Yes' if profile.universal_qr_code_image else 'No'}")
        print(f"  QR UUID: {profile.universal_qr_code}")
        
        if profile.universal_qr_code_image:
            print(f"  Image path: {profile.universal_qr_code_image.name}")
            print(f"  Image URL: {profile.universal_qr_code_image.url}")
        
    except CustomUser.DoesNotExist:
        print(f"✗ User '{username}' not found")
    except Exception as e:
        print(f"✗ Error getting info for {username}: {e}")


def main():
    """Main function demonstrating QR code generation."""
    print("Universal QR Code Generation Examples")
    print("=" * 40)
    
    # Get a sample user for demonstration
    sample_user = CustomUser.objects.first()
    if not sample_user:
        print("No users found in database. Create some users first.")
        return
    
    # Example 1: Generate QR code for a specific user
    print("\n1. Generate QR code for a specific user:")
    print(f"   Using user: {sample_user.username}")
    
    generate_qr_for_single_user(sample_user.username)
    
    # Show user info
    show_user_qr_info(sample_user.username)
    
    # Example 2: Generate QR codes for all users
    print("\n2. Generate QR codes for all users:")
    generate_qr_for_all_users()
    
    print("\n" + "=" * 40)
    print("Examples complete!")
    print("\nTo use the management command:")
    print("python manage.py generate_universal_qr_codes --dry-run")
    print("python manage.py generate_universal_qr_codes")


if __name__ == "__main__":
    main() 