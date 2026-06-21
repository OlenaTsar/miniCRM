from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyViewSet,
    ContactViewSet,
    ContactImportView,
    ContactExportView,
    ProductViewSet,
    DealViewSet,
    PipelineViewSet,
    ActivityViewSet,
    NotificationViewSet,
    ActivityScriptViewSet,
)

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')
router.register('contacts', ContactViewSet, basename='contact')
router.register('products', ProductViewSet, basename='products')
router.register('deals', DealViewSet, basename='deals')
router.register('pipelines', PipelineViewSet, basename='pipelines')
router.register('activities', ActivityViewSet, basename='activities')
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('activity-scripts', ActivityScriptViewSet, basename='activity-scripts')

urlpatterns = [
    path("contacts-import/", ContactImportView.as_view()),
    path("contacts-export/", ContactExportView.as_view()),
]

urlpatterns += router.urls
