from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_remove_subscription_stripe_customer_id_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscription",
            name="stripe_customer",
        ),
        migrations.AddField(
            model_name="subscription",
            name="stripe_customer_id",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.DeleteModel(
            name="StripeCustomer",
        ),
    ]
