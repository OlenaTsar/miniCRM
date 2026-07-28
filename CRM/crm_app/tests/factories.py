import factory
from factory.django import DjangoModelFactory
from crm_app.models import Product


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("sentence")
