from faker import Faker
import random

fake = Faker("en_IN")
regions = ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru"]
tiers = ["Free", "Mobile", "Premium"]

for _ in range(10):
    print(
        fake.name(),
        fake.date_between(start_date="-2y", end_date="today"),
        random.choice(regions),
        random.choice(tiers),
    )