from django.db import models
import uuid

from auth_app.models import User, Team


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    industry = models.CharField(max_length=255, null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField(null=True, blank=True)
    instagram_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='companies',
    )


class ContactStatus(models.TextChoices):
    LEAD = "lead", "Lead"
    QUALIFIED = "qualified", "Qualified"
    PROSPECT = "prospect", "Prospect"
    ACTIVE = "active", "Active"
    DORMANT = "dormant", "Dormant"
    LOST = "lost", "Lost"


class LeadSource(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    FACEBOOK = "facebook", "Facebook"
    GOOGLE_ADS = "google_ads", "Google Ads"
    LINKEDIN = "linkedin", "LinkedIn"
    REFERRAL = "referral", "Referral"
    WEBSITE = "website", "Website"
    COLD_CALL = "cold_call", "Cold Call"
    ORGANIC_SEARCH = "organic_search", "Organic Search"


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    instagram_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=ContactStatus.choices, default=ContactStatus.LEAD)
    lead_source = models.CharField(max_length=20, choices=LeadSource.choices)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='contacts',
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='contacts',
    )
