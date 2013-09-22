from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save


class TrafficUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        user = self.model(email, password)
        return user

    def create_superuser(self, email, password=None)
        user = self.model(email, password)
        return user


class TrafficUser(AbstractBaseUser):
    objects = TrafficUserManager()


class UserProfile(models.Model):
    user = models.ForeignKey('auth.User', unique=True)
    employee_id = models.CharField(max_length=50)


# Auto create profiles upon user creation
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender='auth.User')

