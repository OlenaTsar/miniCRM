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
)

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')
router.register('contacts', ContactViewSet, basename='contact')
router.register('products', ProductViewSet, basename='products')
router.register('deals', DealViewSet, basename='deals')
router.register('pipelines', PipelineViewSet, basename='pipelines')

urlpatterns = [
    path("contacts-import/", ContactImportView.as_view()),
    path("contacts-export/", ContactExportView.as_view()),
]

urlpatterns += router.urls
