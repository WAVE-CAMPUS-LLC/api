import datetime
from datetime import timedelta, date
from django.db import models
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group
from django.utils import timezone
from django.contrib.auth.models import Group
import uuid
import threading
import random
import string
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete
from django.utils.translation import gettext_lazy as _

from accountManagementApp.models import UserProfile
from eventManagementApp.models import SharedEvent
from socialApp.models import CrewMember
from stripeManagementApp.customerSetup import CustomerAccount


from .managers import CustomUserManager


# Create your models here.
class CustomUser(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(
        _("First Name"),
        max_length=50,
        blank=True,
        null=True,
        help_text=(_("First Name")),
        db_index=True,
    )
    last_name = models.CharField(
        _("Last Name"),
        max_length=50,
        blank=True,
        null=True,
        help_text=(_("Last Name")),
        db_index=True,
    )
    email = models.EmailField(
        _("Email"), unique=True, blank=False, null=False, help_text=(_("Email"))
    )
    username = models.CharField(
        _("Username"),
        max_length=15,
        blank=False,
        null=False,
        unique=True,
        help_text=(_("Username")),
        db_index=True,
    )

    date_joined = models.DateField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)

    # The generation of a random user id for every user that signs up.
    user_id = models.UUIDField(
        _("User ID"), default=uuid.uuid4, editable=False, unique=True
    )

    email_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)

    customer_id = models.CharField(max_length=255, null=True, blank=True)
    connectAccountCreated = models.BooleanField(default=False)
    connectAccountID = models.CharField(max_length=255, null=True, blank=True)

    def suspend(self):
        suspend_group, created = Group.objects.get_or_create(name="Suspend")
        member_group = Group.objects.get(name="Member")
        self.groups.remove(member_group)
        self.groups.add(suspend_group)
        self.is_suspended = True
        self.save()

    def remove_suspension_OR_ban(self):
        if self.is_suspended:
            suspend_group = Group.objects.get(name="Suspend")
            member_group = Group.objects.get(name="Member")

            if self.is_suspended:
                self.groups.remove(suspend_group)
                self.is_suspended = False

            self.groups.add(member_group)
            self.save()

    def get_shared_events(self):
        return SharedEvent.objects.filter(receiver=self.user)

    def generate_username_from_email(self):
        """
        Auto-generate username from email in format: prefix#0000
        Example: enoshlartey3@gmail.com -> enlart#0034
        """
        if not self.email:
            return None

        # Extract email prefix (part before @)
        email_prefix = self.email.split("@")[0].lower()

        # Remove numbers and special characters, keep only letters
        clean_prefix = "".join(char for char in email_prefix if char.isalpha())

        # Take up to 6 characters for the base username
        base_username = clean_prefix[:6] if len(clean_prefix) >= 6 else clean_prefix

        # Generate 4 random digits
        random_digits = "".join(random.choices(string.digits, k=4))

        # Create username with # separator
        generated_username = f"{base_username}#{random_digits}"

        # Ensure uniqueness - regenerate digits if username already exists
        max_attempts = 100  # Prevent infinite loop
        attempts = 0
        while (
            CustomUser.objects.filter(username=generated_username).exists()
            and attempts < max_attempts
        ):
            random_digits = "".join(random.choices(string.digits, k=4))
            generated_username = f"{base_username}#{random_digits}"
            attempts += 1

        return generated_username

    @classmethod
    def generate_username_for_email(cls, email):
        """
        Class method to generate username for any given email
        Useful for forms or other contexts where you need to generate
        a username before creating the user instance
        """
        if not email:
            return None

        # Extract email prefix (part before @)
        email_prefix = email.split("@")[0].lower()

        # Remove numbers and special characters, keep only letters
        clean_prefix = "".join(char for char in email_prefix if char.isalpha())

        # Take up to 6 characters for the base username
        base_username = clean_prefix[:6] if len(clean_prefix) >= 6 else clean_prefix

        # Generate 4 random digits
        random_digits = "".join(random.choices(string.digits, k=4))

        # Create username with # separator
        generated_username = f"{base_username}#{random_digits}"

        # Ensure uniqueness - regenerate digits if username already exists
        max_attempts = 100  # Prevent infinite loop
        attempts = 0
        while (
            cls.objects.filter(username=generated_username).exists()
            and attempts < max_attempts
        ):
            random_digits = "".join(random.choices(string.digits, k=4))
            generated_username = f"{base_username}#{random_digits}"
            attempts += 1

        return generated_username

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "username",
    ]

    class Meta:
        default_permissions = ()

        indexes = [
            GinIndex(
                fields=["username"],
                name="username_gin_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                fields=["first_name"],
                name="first_name_gin_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                fields=["last_name"],
                name="last_name_gin_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]

        verbose_name = "Member Account"
        verbose_name_plural = "Member Accounts"

    def save(self, *args, **kwargs):
        # Auto-generate username if not provided
        if not self.username and self.email:
            self.username = self.generate_username_from_email()

        if not self.customer_id:
            from stripeManagementApp.customerSetup import CustomerAccount

            existing_customer = CustomerAccount.searchCustomerAccount(self.email)
            if existing_customer:
                self.customer_id = existing_customer.id
            else:
                new_customer = CustomerAccount.createCustomerAccount(
                    None, self.email, self.first_name, self.last_name
                )
                self.customer_id = new_customer.id

        super(CustomUser, self).save(*args, **kwargs)

    def delete_stripe_customer(self):
        if self.customer_id:
            CustomerAccount.deleteCustomerAccount(self.customer_id)

    def __str__(self):
        return self.email


@receiver(pre_save, sender=CustomUser)
def generate_user_id(sender, instance, **kwargs):
    if not instance.user_id:
        instance.user_id = uuid.uuid4()


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def add_super_admin_group(sender, instance, created, **kwargs):
    # Check if the user is created and is a superuser
    if created and instance.is_superuser:
        # Ensure the "Super Admin" group exists
        super_admin_group, created = Group.objects.get_or_create(name="Super Admin")
        admin_group, created = Group.objects.get_or_create(name="Admin")
        # Add the user to the "Super Admin" group
        instance.groups.add(super_admin_group)
        instance.groups.add(admin_group)


@receiver(post_delete, sender=CustomUser)
def delete_stripe_customer(sender, instance, **kwargs):
    instance.delete_stripe_customer()


class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=7)
    is_verified = models.BooleanField(default=False)
    expiration_date = models.DateTimeField()

    def __str__(self):
        return self.verification_code
