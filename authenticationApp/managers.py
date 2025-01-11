from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set!"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superadmin', True)

        # Create or get the "Super Admin" group
        super_admin_group, created = Group.objects.get_or_create(name="Super Admin")
        
        # Create the superuser
        user = self.create_user(email, password, **extra_fields)
        
        # Add the user to the "Super Admin" group
        user.groups.add(super_admin_group)
        
        return user
    
    
    # def create_superadmin(self, email, password, **extra_field):
    #     extra_field.setdefault('is_staff', True)
    #     extra_field.setdefault('is_superuser', True)
    #     extra_field.setdefault('is_active', True)
    #     extra_field.setdefault('is_superadmin', True)
        
    #     if extra_field.get('is_staff') is not True:
    #         raise ValueError(_("Superadmin must have is_staff=True."))
    #     if extra_field.get('is_superuser') is not True:
    #         raise ValueError(_("Superadmin must have is_superuser=True."))
    #     if extra_field.get('is_superadmin') is not True:
    #         raise ValueError(_("Superadmin must have is_superadmin=True."))
        
    #     return self.create_user(email, password, **extra_field)