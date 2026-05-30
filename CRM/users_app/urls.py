from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter()
router.register('', UserViewSet, basename='user')

urlpatterns = router.urls

# urlpatterns += [
#     path('me/', MeAPIView.as_view()),
# ]
