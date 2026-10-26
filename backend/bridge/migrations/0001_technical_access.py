from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="HostingTechnicalLogin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_id", models.PositiveBigIntegerField(unique=True)),
                ("subject_id", models.PositiveBigIntegerField()),
                ("binding_ref", models.UUIDField()),
                ("username", models.CharField(max_length=32, unique=True)),
                ("password_hash", models.CharField(max_length=256)),
                ("enabled", models.BooleanField(default=False)),
                ("failed_attempts", models.PositiveSmallIntegerField(default=0)),
                ("locked_until", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_at", models.DateTimeField(auto_now=True)),
            ],
            options={"indexes": [models.Index(fields=["subject_id", "service_id"], name="opanel_tech_owner_ix")]},
        ),
        migrations.CreateModel(
            name="HostingLoginThrottle",
            fields=[
                ("fingerprint", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("failure_count", models.PositiveSmallIntegerField(default=0)),
                ("window_started", models.DateTimeField()),
                ("locked_until", models.DateTimeField(null=True, blank=True)),
            ],
        ),
    ]
