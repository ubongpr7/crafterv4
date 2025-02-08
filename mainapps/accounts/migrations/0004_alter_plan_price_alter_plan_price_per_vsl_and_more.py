from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_plan_subscription_remove_credit_user_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plan",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="plan",
            name="price_per_vsl",
            field=models.DecimalField(decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="plan",
            name="stripe_price_id",
            field=models.CharField(max_length=255, null=True),
        ),
    ]
