from django.core.management.base import BaseCommand

from cars.models import Car


INVENTORY = [
    {
        "stock_number": "NL-2401",
        "make": "Porsche",
        "model": "911 Carrera",
        "year": 2022,
        "price": "118900.00",
        "rental_daily_rate": "195.00",
        "mileage": 8420,
        "transmission": "Automatic",
        "fuel_type": "Gasoline",
        "body_style": "Coupe",
        "exterior_color": "Chalk",
        "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=80",
        "description": "A beautifully kept 911 Carrera with a clean history.",
        "featured": True,
    },
    {
        "stock_number": "NL-2402",
        "make": "BMW",
        "model": "M4 Competition",
        "year": 2023,
        "price": "82900.00",
        "rental_daily_rate": "155.00",
        "mileage": 6100,
        "transmission": "Automatic",
        "fuel_type": "Gasoline",
        "body_style": "Coupe",
        "exterior_color": "Isle of Man Green",
        "image_url": "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1000&q=80",
        "description": "A sharp, low-mileage M4 Competition, ready for the open road.",
        "featured": True,
    },
    {
        "stock_number": "NL-2403",
        "make": "Mercedes-Benz",
        "model": "E-Class",
        "year": 2022,
        "price": "58900.00",
        "rental_daily_rate": "125.00",
        "mileage": 12400,
        "transmission": "Automatic",
        "fuel_type": "Hybrid",
        "body_style": "Sedan",
        "exterior_color": "Obsidian Black",
        "image_url": "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=1000&q=80",
        "description": "Effortless comfort and considered details in every mile.",
        "featured": False,
    },
    {
        "stock_number": "NL-2404",
        "make": "Audi",
        "model": "RS 5 Sportback",
        "year": 2023,
        "price": "76900.00",
        "rental_daily_rate": "145.00",
        "mileage": 9300,
        "transmission": "Automatic",
        "fuel_type": "Gasoline",
        "body_style": "Sportback",
        "exterior_color": "Nardo Grey",
        "image_url": "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=1000&q=80",
        "description": "Everyday practicality with a little extra spirit.",
        "featured": False,
    },
    {
        "stock_number": "NL-2405",
        "make": "BMW",
        "model": "i4 eDrive40",
        "year": 2024,
        "price": "61900.00",
        "rental_daily_rate": "135.00",
        "mileage": 3200,
        "transmission": "Automatic",
        "fuel_type": "Electric",
        "body_style": "Sedan",
        "exterior_color": "Brooklyn Grey",
        "image_url": "https://images.unsplash.com/photo-1556189250-72ba954cfc2b?auto=format&fit=crop&w=1000&q=80",
        "description": "A near-new all-electric drive with an impressive range.",
        "featured": True,
    },
    {
        "stock_number": "NL-2406",
        "make": "Audi",
        "model": "Q5 Premium Plus",
        "year": 2021,
        "price": "41900.00",
        "rental_daily_rate": "105.00",
        "mileage": 18700,
        "transmission": "Automatic",
        "fuel_type": "Gasoline",
        "body_style": "SUV",
        "exterior_color": "Glacier White",
        "image_url": "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?auto=format&fit=crop&w=1000&q=80",
        "description": "A versatile, comfortable SUV for wherever the week takes you.",
        "featured": False,
    },
]


class Command(BaseCommand):
    help = "Create or update the sample dealership inventory."

    def handle(self, *args, **options):
        for car_data in INVENTORY:
            stock_number = car_data["stock_number"]
            defaults = {key: value for key, value in car_data.items() if key != "stock_number"}
            Car.objects.update_or_create(stock_number=stock_number, defaults=defaults)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(INVENTORY)} sample cars."))
