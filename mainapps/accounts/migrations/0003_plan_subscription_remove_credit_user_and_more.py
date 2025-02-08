from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_credit_product_user_verification_token"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("stripe_price_id", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=50)),
                ("price", models.DecimalField(decimal_places=2, max_digits=5)),
                ("price_per_vsl", models.DecimalField(decimal_places=2, max_digits=5)),
                ("vsl_limit", models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("stripe_subscription_id", models.CharField(max_length=255, null=True)),
                ("stripe_customer_id", models.CharField(max_length=255, null=True)),
                ("credits", models.IntegerField(default=0)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="accounts.plan"
                    ),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="credit",
            name="user",
        ),
        migrations.RemoveField(
            model_name="mystripemodel",
            name="stripe_subscription",
        ),
        migrations.DeleteModel(
            name="SubscriptionPlan",
        ),
        migrations.DeleteModel(
            name="VlcPlan",
        ),
        migrations.RemoveField(
            model_name="user",
            name="allowed_videos",
        ),
        migrations.RemoveField(
            model_name="user",
            name="generated_videos",
        ),
        migrations.DeleteModel(
            name="Credit",
        ),
        migrations.DeleteModel(
            name="MyStripeModel",
        ),
        migrations.DeleteModel(
            name="StripeSubscription",
        ),
        migrations.AddField(
            model_name="user",
            name="subscription",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="accounts.subscription",
            ),
        ),
    ]
