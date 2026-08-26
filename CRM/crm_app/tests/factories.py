from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from crm_app.models import (
    Company,
    Contact,
    ContactStatus,
    LeadSource,
    Product,
    Pipeline,
    Deal,
    ActivityScript,
    Activity,
    ActivityType,
    DealStatus,
    Currency,
    PipelineStage,
    Archive,
    ArchivingType,
)
from auth_app.tests.factories import UserFactory


class CompanyFactory(DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Company {n}")
    description = factory.Faker("sentence")
    industry = factory.Faker("sentence")
    website = factory.Faker("url")
    email = factory.Sequence(lambda n: f"company{n}@test.com")
    instagram_url = factory.Faker("url")
    facebook_url = factory.Faker("url")
    created_by = factory.SubFactory(UserFactory)


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = Contact

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"contact{n}@test.com")
    phone = factory.Faker("numerify", text="###############")
    city = factory.Faker("city")
    instagram_url = factory.Faker("url")
    facebook_url = factory.Faker("url")
    status = ContactStatus.LEAD
    lead_source = LeadSource.INSTAGRAM
    company = factory.SubFactory(CompanyFactory)
    created_by = factory.SubFactory(UserFactory)


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("sentence")


class PipelineFactory(DjangoModelFactory):
    class Meta:
        model = Pipeline

    name = factory.Sequence(lambda n: f"Pipeline {n}")
    product = factory.SubFactory(ProductFactory)
    assigned_to = factory.SubFactory(UserFactory)


class DealFactory(DjangoModelFactory):
    class Meta:
        model = Deal

    name = factory.Sequence(lambda n: f"Deal {n}")
    description = factory.Faker("sentence")
    status = DealStatus.NEW
    amount = factory.Faker("pydecimal", left_digits=6, right_digits=2, positive=True)
    currency = Currency.UAH
    expected_close_date = None
    stage = PipelineStage.NEW_LEAD

    pipeline = factory.SubFactory(PipelineFactory)
    product = factory.LazyAttribute(lambda obj: obj.pipeline.product)
    contact = factory.SubFactory(ContactFactory)
    company = None
    assigned_to = factory.SubFactory(UserFactory)


class ActivityScriptFactory(DjangoModelFactory):
    class Meta:
        model = ActivityScript

    title = factory.Sequence(lambda n: f"Activity {n}")
    text = factory.Faker("text")
    attachment = None
    activity_type = ActivityType.CALL
    stage = PipelineStage.NEW_LEAD
    product = factory.SubFactory(ProductFactory)
    created_by = factory.SubFactory(UserFactory)


class ActivityFactory(DjangoModelFactory):
    class Meta:
        model = Activity

    title = factory.Sequence(lambda n: f"Activity {n}")
    description = factory.Faker("sentence")
    activity_type = ActivityType.CALL
    outcome = None
    due_date = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=2))

    assigned_to = factory.SubFactory(UserFactory)
    contact = factory.SubFactory(ContactFactory)
    deal = factory.SubFactory(DealFactory)
    script = factory.SubFactory(ActivityScriptFactory)


class ArchiveFactory(DjangoModelFactory):
    class Meta:
        model = Archive

    archiving_type = ArchivingType.MANUAL

    archived_by = factory.SubFactory(UserFactory)
