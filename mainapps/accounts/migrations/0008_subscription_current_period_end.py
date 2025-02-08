from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_remove_subscription_stripe_customer_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="current_period_end",
            field=models.IntegerField(default=0),
        ),
    ]
