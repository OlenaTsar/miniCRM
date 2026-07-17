import factory
from factory.django import DjangoModelFactory
from auth_app.models import User, Team


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"Team {n}")


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        # skip_postgeneration_save = True  # буде необхідним для нової версії factory_boy

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "pass12345")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = "employee"
    is_active = True
    is_verified = True
    team = factory.SubFactory(TeamFactory)
