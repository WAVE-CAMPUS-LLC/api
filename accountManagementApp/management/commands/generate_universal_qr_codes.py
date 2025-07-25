from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
import sys


class Command(BaseCommand):
    help = 'Generate universal QR codes for existing users who do not have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Generate QR code for a specific user ID only',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Generate QR code for a specific username only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate QR codes even if they already exist',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of users to process in each batch (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually generating QR codes',
        )

    def handle(self, *args, **options):
        """
        Main command handler that orchestrates the QR code generation process.
        """
        try:
            # Get users to process based on command arguments
            users_to_process = self.get_users_to_process(options)
            
            if not users_to_process.exists():
                self.stdout.write(
                    self.style.WARNING('No users found matching the specified criteria.')
                )
                return
            
            # Ensure all users have profiles
            profiles_created = self.ensure_all_users_have_profiles(users_to_process)
            if profiles_created > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Created {profiles_created} missing user profiles.')
                )
            
            # Get user profiles that need QR codes
            profiles_queryset = UserProfile.objects.filter(
                user__in=users_to_process
            ).select_related('user')
            
            if not options['force']:
                # Only process users without QR codes
                profiles_queryset = profiles_queryset.filter(universal_qr_code_image__isnull=True)
            
            if not profiles_queryset.exists():
                self.stdout.write(
                    self.style.SUCCESS('All specified users already have universal QR codes!')
                )
                return
            
            # Show what would be done in dry-run mode
            if options['dry_run']:
                self.show_dry_run_results(profiles_queryset, options)
                return
            
            # Process QR code generation
            self.stdout.write(f"Processing {profiles_queryset.count()} user profiles...")
            
            batch_size = options['batch_size']
            total_processed = 0
            total_success = 0
            total_errors = 0
            
            # Process in batches
            for i in range(0, profiles_queryset.count(), batch_size):
                batch = profiles_queryset[i:i + batch_size]
                batch_stats = self.process_batch(batch, options)
                
                total_processed += batch_stats['processed']
                total_success += batch_stats['success']
                total_errors += batch_stats['errors']
                
                # Progress update
                self.stdout.write(
                    f"Batch complete: {total_processed}/{profiles_queryset.count()} "
                    f"(Success: {total_success}, Errors: {total_errors})"
                )
            
            # Final summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nQR code generation complete!\n'
                    f'Total processed: {total_processed}\n'
                    f'Successful: {total_success}\n'
                    f'Errors: {total_errors}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')

    def get_users_to_process(self, options):
        """
        Get the queryset of users to process based on command options.
        """
        if options['user_id']:
            return CustomUser.objects.filter(id=options['user_id'])
        elif options['username']:
            return CustomUser.objects.filter(username=options['username'])
        else:
            return CustomUser.objects.all()

    def ensure_all_users_have_profiles(self, users_queryset):
        """
        Ensure all users have UserProfile instances.
        Returns the number of profiles created.
        """
        profiles_created = 0
        
        for user in users_queryset:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={}
            )
            if created:
                profiles_created += 1
                self.stdout.write(f"Created profile for user: {user.username}")
        
        return profiles_created

    def show_dry_run_results(self, profiles_queryset, options):
        """
        Show what would be done without actually doing it.
        """
        self.stdout.write(
            self.style.WARNING('=== DRY RUN MODE - No changes will be made ===\n')
        )
        
        for profile in profiles_queryset:
            has_qr = bool(profile.universal_qr_code_image)
            action = "Regenerate" if (has_qr and options['force']) else "Generate"
            
            self.stdout.write(
                f"Would {action.lower()} QR code for: {profile.user.username} "
                f"(Current QR: {'Yes' if has_qr else 'No'})"
            )
        
        self.stdout.write(
            f"\nTotal users that would be processed: {profiles_queryset.count()}"
        )
        self.stdout.write(
            self.style.WARNING('\nRun without --dry-run to execute the changes.')
        )

    def process_batch(self, batch, options):
        """
        Process a batch of user profiles for QR code generation.
        """
        processed = 0
        success = 0
        errors = 0
        
        # Temporarily disconnect the profile picture signal to avoid conflicts
        from accountManagementApp.signals import create_profile_picture
        post_save.disconnect(create_profile_picture, sender=UserProfile)
        
        try:
            with transaction.atomic():
                for profile in batch:
                    try:
                        # Skip users with incomplete information
                        if not profile.user or not profile.user.username:
                            errors += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ✗ Skipping profile with incomplete user info'
                                )
                            )
                            processed += 1
                            continue
                        
                        has_qr = bool(profile.universal_qr_code_image)
                        action = "Regenerate" if (has_qr and options['force']) else "Generate"
                        
                        # Generate the QR code
                        success_result = profile.generate_universal_qr_code()
                        
                        if success_result:
                            # Save only the QR code fields to avoid triggering other signals
                            profile.save(update_fields=['universal_qr_code', 'universal_qr_code_image'])
                            success += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Generated QR code for: {profile.user.username}'
                                )
                            )
                        else:
                            errors += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ✗ Failed to generate QR code for: {profile.user.username}'
                                )
                            )
                        
                    except Exception as e:
                        errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Error processing {profile.user.username}: {str(e)}'
                            )
                        )
                    
                    processed += 1
        
        finally:
            # Reconnect the signal
            post_save.connect(create_profile_picture, sender=UserProfile)
        
        return {
            'processed': processed,
            'success': success,
            'errors': errors
        } 