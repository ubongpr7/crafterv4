from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Plan(models.Model):
    stripe_price_id = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    price_per_vsl = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    vsl_limit = models.IntegerField(default=0)

    class Meta:
        ordering = ['id'] 

class StripeCustomer(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, null=True)
    stripe_customer_id = models.CharField(max_length=255)


class Subscription(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255, null=True)
    customer = models.ForeignKey(StripeCustomer, on_delete=models.CASCADE, null=True)
    credits = models.IntegerField(default=0)
    current_period_end = models.IntegerField(default=0)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # def create_superuser(self, email, password=None, **extra_fields):
    #     extra_fields.setdefault("is_staff", True)
    #     extra_fields.setdefault("is_superuser", True)
    #     return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
            extra_fields.setdefault("is_staff", True)
            extra_fields.setdefault("is_superuser", True)

            if not extra_fields.get("is_staff"):
                raise ValueError("Superuser must have is_staff=True.")
            if not extra_fields.get("is_superuser"):
                raise ValueError("Superuser must have is_superuser=True.")

            user = self.create_user(email, password, **extra_fields)

            try:
                admin_plan = Plan.objects.get(id=4) 
                stripe_customer = StripeCustomer.objects.create(user=user, stripe_customer_id=f"admin_{user.id}")
                subscription = Subscription.objects.create(
                    plan=admin_plan,
                    stripe_subscription_id=f"sub_admin_{user.id}",
                    customer=stripe_customer,
                    credits=admin_plan.vsl_limit,  
                )

                user.subscription = subscription
                user.save()
            except Plan.DoesNotExist:
                return user
                # raise ValueError("Admin plan with ID=4 does not exist. Please create it first.")


            return user

class User(AbstractUser):
    email = models.EmailField(unique=True, null=False, blank=False)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)

    def can_generate_video(self):
        return self.subscription.credits >= 1
