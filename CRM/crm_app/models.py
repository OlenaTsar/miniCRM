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


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    description = models.TextField(null=True, blank=True)

    teams = models.ManyToManyField(
        Team,
        blank=True,
        related_name='products',
    )


class Pipeline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='pipelines',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='pipelines',
    )


class PipelineStage(models.TextChoices):
    NEW_LEAD = "new_lead", "New Lead"
    QUALIFICATION = "qualification", "Qualification"
    PROPOSAL_SENT = "proposal_sent", "Proposal Sent"
    NEGOTIATION = "negotiation", "Negotiation"
    CLOSED_WON = "closed_won", "Closed Won"
    CLOSED_LOST = "closed_lost", "Closed Lost"


class DealStatus(models.TextChoices):
    NEW = "new", "New"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    CLOSED = "closed", "Closed"


class Currency(models.TextChoices):
    UAH = "UAH", "Ukrainian Hryvnia"
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British Pound"
    PLN = "PLN", "Polish Zloty"


class Deal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=DealStatus.choices, default=DealStatus.NEW)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.UAH)
    expected_close_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stage = models.CharField(max_length=20, choices=PipelineStage.choices, default=PipelineStage.NEW_LEAD)
    closed_at = models.DateTimeField(null=True, blank=True)

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='deals',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=False,
        blank=True,
        related_name='deals',
    )
    contacts = models.ManyToManyField(
        Contact,
        blank=True,
        related_name='deals',
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='deals',
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
        related_name='deals',
    )


class DealStageHistory(models.Model):
    # для збереження історії зміни stage
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    old_stage = models.CharField(max_length=20, choices=PipelineStage.choices, null=False)
    new_stage = models.CharField(max_length=20, choices=PipelineStage.choices, null=False)
    changed_at = models.DateTimeField(auto_now_add=True)

    deal = models.ForeignKey(
        Deal,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="stage_history",
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        related_name="deal_stage_history",
    )


class ActivityType(models.TextChoices):
    CALL = "call", "Call"
    EMAIL = "email", "Email"
    MEETING = "meeting", "Meeting"
    TASK = "task", "Task"
    PROPOSAL = "proposal", "Send a proposal"
    CONTRACT = "contract", "Signing the contract"
    OTHER = "other", "Other"


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices, null=False, blank=False)
    outcome = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=False, blank=False)
    completed_at = models.DateTimeField(null=True, blank=True, default=None)

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        blank=True,
        related_name='activities',
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='activities',
    )
    deal = models.ForeignKey(
        Deal,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="activities",
    )


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=20, choices=Action.choices)
    old_data = models.JSONField(null=True)  # null при created
    new_data = models.JSONField(null=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    activity = models.ForeignKey(
        Activity,
        null=False,
        on_delete=models.CASCADE,
        related_name="activity_log",
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_logs"
    )


class Notification(models.Model):
    class Meta:
        # для пришвидшення пошуку у бд
        indexes = [
            models.Index(
                fields=["sent_at", "notify_at"],
                name="notification_read_notify_idx",
            ),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notify_at = models.DateTimeField(null=False, blank=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='notifications',
    )
    activity = models.OneToOneField(
        Activity,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="notification",
    )


class ActivityScript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    text = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to="attachments/", null=True, blank=True)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices, null=False, blank=False)
    stage = models.CharField(max_length=20, choices=PipelineStage.choices, null=False, blank=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='notifications',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='activity_scripts',
    )
