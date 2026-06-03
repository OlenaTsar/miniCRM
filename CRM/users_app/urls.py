from rest_framework.routers import DefaultRouter

from .views import UserViewSet, TeamViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('teams', TeamViewSet, basename='team')

urlpatterns = router.urls
