"""Creates the 3 appliance categories with example services from the requirements doc."""
from django.core.management.base import BaseCommand
from core.models import ApplianceCategory, Service, User, TechnicianProfile


class Command(BaseCommand):
    help = "Seed default appliance categories, services and demo accounts"

    def handle(self, *args, **options):
        cat_ac = ApplianceCategory.objects.get_or_create(name="AC", defaults={"icon": "❄️", "description": "Air Conditioner repair & service"})[0]
        cat_tv = ApplianceCategory.objects.get_or_create(name="TV", defaults={"icon": "📺", "description": "Television repair & service"})[0]
        cat_fr = ApplianceCategory.objects.get_or_create(name="Fridge", defaults={"icon": "🧊", "description": "Refrigerator repair & service"})[0]

        services = [
            (cat_ac, "AC General Service", 500), (cat_ac, "AC Installation", 1500),
            (cat_ac, "AC Repair", 700), (cat_ac, "AC Gas Refilling", 1200),
            (cat_ac, "AC Water Leakage", 600), (cat_ac, "AC Cooling Problem", 800),
            (cat_ac, "AC Maintenance", 550),
            (cat_tv, "TV Display Issue", 900), (cat_tv, "TV Not Turning On", 600),
            (cat_tv, "Screen Problem", 1100), (cat_tv, "Sound Problem", 500),
            (cat_tv, "Software Issue", 450), (cat_tv, "Installation", 700),
            (cat_fr, "Cooling Problem", 650), (cat_fr, "Gas Leakage", 1400),
            (cat_fr, "Compressor Problem", 1800), (cat_fr, "Water Leakage", 500),
            (cat_fr, "Ice Formation", 450), (cat_fr, "Door Problem", 400),
            (cat_fr, "General Maintenance", 500),
        ]
        for cat, name, price in services:
            Service.objects.get_or_create(category=cat, name=name, defaults={"base_price": price})

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123", role=User.Role.ADMIN)
            self.stdout.write("Created superuser admin/admin123")
        if not User.objects.filter(username="customer1").exists():
            User.objects.create_user("customer1", "cust@example.com", "cust123",
                                     role=User.Role.CUSTOMER, phone="9000000001")
            self.stdout.write("Created customer customer1/cust123")
        if not User.objects.filter(username="tech1").exists():
            tech = User.objects.create_user("tech1", "tech@example.com", "tech123",
                                            role=User.Role.TECHNICIAN, phone="9000000002")
            profile = TechnicianProfile.objects.create(user=tech, experience_years=5, is_available=True)
            profile.expertise.set([cat_ac, cat_tv, cat_fr])
            profile.approval_status = "APPROVED"
            profile.save()
            self.stdout.write("Created technician tech1/tech123 (approved)")

        self.stdout.write(self.style.SUCCESS("Seeding complete."))