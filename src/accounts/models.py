from django.contrib.auth.models import AbstractUser
from django.db import models

GOVERNMENT_CHOICES = [
    ('1', 'Cairo'),
    ('2', 'Alexandria'),
    ('3', 'Kafr El Sheikh'),
    ('4', 'Dakahleya'),
    ('5', 'Sharkeya'),
    ('6', 'Gharbeya'),
    ('7', 'Monefeya'),
    ('8', 'Qalyubia'),
    ('9', 'Giza'),
    ('10', 'Bani-Sweif'),
    ('11', 'Fayoum'),
    ('12', 'Menya'),
    ('13', 'Assiut'),
    ('14', 'Sohag'),
    ('15', 'Qena'),
    ('16', 'Luxor'),
    ('17', 'Aswan'),
    ('18', 'Red Sea'),
    ('19', 'Behera'),
    ('20', 'Ismailia'),
    ('21', 'Suez'),
    ('22', 'Port-Said'),
    ('23', 'Damietta'),
    ('24', 'Marsa Matrouh'),
    ('25', 'Al-Wadi Al-Gadid'),
    ('26', 'North Sinai'),
    ('27', 'South Sinai'),
]

class User(AbstractUser):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name if self.name else self.username
    
    class Meta:
        ordering = ['-date_joined']


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=150,null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    government = models.CharField(choices=GOVERNMENT_CHOICES, max_length=2,null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=255,null=True, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.address}"

    def save(self, *args, **kwargs):
        from django.db import transaction
        
        with transaction.atomic():
            # If this address is being set as default
            if self.is_default:
                # Get all other addresses for this user
                other_addresses = UserAddress.objects.filter(user=self.user)
                
                # If this is an existing instance, exclude it from the update
                if self.pk:
                    other_addresses = other_addresses.exclude(pk=self.pk)
                
                # Update all other addresses to not be default (atomic)
                other_addresses.update(is_default=False)
            
            # If this is the first address being created for the user, set it as default
            # Use select_for_update to prevent race conditions
            elif not UserAddress.objects.filter(user=self.user).exists():
                self.is_default = True
                
            super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'User Addresses'
        ordering = ['-is_default', '-created_at']








