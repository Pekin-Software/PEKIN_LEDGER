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
# | GET    | `/store/{id}/list-staff/`   | List users assigned to a store                             |
# | DELETE | `/store/{id}/remove-staff/` | Remove a user from a store (requires `"username"` in body) |
# POST	/store/{pk}/add-inventory/	Add or update inventory in the store's warehouse	Authenticated + Admin
# GET	/store/{pk}/inventory/	List inventory for a store's warehouse	Authenticated + Admin/Assigned Staff
# GET	/store/main-inventory/	List inventory for a general warehouse	Authenticated + Admin
#GET /api/store/main-inventory/?exclude_store_id=store_id -return data not in the store