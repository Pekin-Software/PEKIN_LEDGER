from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet


router = DefaultRouter()
router.register(r'store', StoreViewSet, basename='manage-store')

urlpatterns = [
    path('api/', include(router.urls)),
]

# | Method | Endpoint                   | Action             |
# | ------ | ------------------------ | ------------------ |
# | GET    | `/store/`                | List stores        |
# | GET    | `/store/{id}/`           | Retrieve store     |
# | PUT    | `/store/{id}/`           | Update store       |
# | PATCH  | `/store/{id}/`           | Partial update     |
# | POST   | `/store/create-store/`   | Custom create      |
# | POST   | `/store/{id}/add-staff/` | Add/reassign staff |
# | GET    | `/stores/{id}/list-staff/`   | List users assigned to a store                             |
# | DELETE | `/stores/{id}/remove-staff/` | Remove a user from a store (requires `"username"` in body) |
