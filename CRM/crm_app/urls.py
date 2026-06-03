from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, ContactViewSet, ContactImportView, ContactExportView

router = DefaultRouter()
router.register('companies', CompanyViewSet, basename='company')
router.register('contacts', ContactViewSet, basename='contact')

urlpatterns = [
    path("contacts-import/", ContactImportView.as_view()),
    path("contacts-export/", ContactExportView.as_view()),
]

urlpatterns += router.urls
