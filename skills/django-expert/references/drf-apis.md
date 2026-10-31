# Django REST Framework and django-ninja

Building JSON APIs on Django 6.x with Django REST Framework 3.18.3: serializers, viewsets, routers, permissions, authentication, throttling, pagination, filtering and error shape, with a short comparison to django-ninja 1.7.3. Snippets were run against Django 6.1.2 (2026-10). Resource modelling and status-code policy belong to rest-api-expert.

## Contents

1. [Versions and settings](#1-versions-and-settings)
2. [Serializers](#2-serializers)
3. [Viewsets and routers](#3-viewsets-and-routers)
4. [Authentication and permissions](#4-authentication-and-permissions)
5. [Throttling](#5-throttling)
6. [Pagination and filtering](#6-pagination-and-filtering)
7. [Errors and validation](#7-errors-and-validation)
8. [Testing endpoints](#8-testing-endpoints)
9. [Schema and docs](#9-schema-and-docs)
10. [django-ninja](#10-django-ninja)

## 1. Versions and settings

- DRF 3.18.3 (2026-10) lists Django 5.2, 6.0 and 6.1 and Python 3.10+ in its package metadata; 3.18.0 dropped Django 4.2, 5.0 and 5.1. Read the 3.18 release notes before upgrading from 3.15 or earlier: the error format for `many=True` list serializers changed in 3.18.0, with a compatibility setting added in 3.18.1.
- Install with `pip install djangorestframework`, add `"rest_framework"` to `INSTALLED_APPS`, and set defaults once.

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/hour", "user": "1000/hour"},
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
}
```

- `CursorPagination` orders by `-created` unless the paginator subclass sets `ordering`; the field must exist and be indexed, so set it per view when models differ.
- Remove the browsable API renderer in production if it is not needed: `"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]`.

## 2. Serializers

```python
from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price_cents", "stock", "category", "category_name", "created"]
        read_only_fields = ["id", "created"]

    def validate_price_cents(self, value):
        if value > 1_000_000:
            raise serializers.ValidationError("price too large")
        return value
```

- List `fields` explicitly. `fields = "__all__"` exposes new model columns automatically, including internal ones.
- `read_only_fields`, `write_only` (passwords), `extra_kwargs` control direction. Never accept `is_staff`, `owner` or similar from the client; set them in `perform_create` from `request.user`.
- Validation order: field validators, `validate_<field>()`, then `validate(self, attrs)` for cross-field rules. Raise `serializers.ValidationError`, not Django's `ValidationError`.
- Reading a nested relation (`category_name` above) costs a query per row unless the view uses `select_related("category")`. For reverse relations use `prefetch_related` and a nested serializer with `many=True, read_only=True`.
- `SerializerMethodField` runs Python per row: avoid queries inside it. Annotate in the queryset and read the annotation with a plain field (`serializers.IntegerField(read_only=True)`).
- Writable nested serializers need explicit `create()` / `update()`; wrap multi-row writes in `transaction.atomic`.
- Use a separate input serializer for actions that are not CRUD (see the `restock` action below) instead of reading `request.data` directly.
- `ModelSerializer` generates unique and `UniqueConstraint` validators; check that conditional constraints behave as intended after upgrades (3.18.2 fixed several validator edge cases).

## 3. Viewsets and routers

```python
from django.db.models import F
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle


class ProductCursorPagination(CursorPagination):
    page_size = 50
    ordering = "-created"


class RestockSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1, max_value=10_000)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = ProductCursorPagination
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "products"

    def get_queryset(self):
        return Product.objects.select_related("category")

    @action(detail=True, methods=["post"], throttle_scope="restock")
    def restock(self, request, pk=None):
        product = self.get_object()
        body = RestockSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        Product.objects.filter(pk=product.pk).update(
            stock=F("stock") + body.validated_data["amount"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
```

```python
# urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
urlpatterns = [path("api/", include(router.urls))]
```

- `ModelViewSet` gives list, retrieve, create, update, partial_update, destroy. Use `ReadOnlyModelViewSet`, or mix in only `mixins.ListModelMixin` and `GenericViewSet`, when writes are not wanted.
- Always filter the queryset in `get_queryset()` by the requester (`.filter(owner=self.request.user)`) so object lookups cannot reach other users' rows. Return 404 rather than 403 for foreign objects by filtering.
- `get_serializer_class()` switches serializers per action (`list` slim, `retrieve` detailed, `create` input).
- Hook points: `perform_create(serializer)` (set owner), `perform_update`, `perform_destroy`.
- Async views in DRF: `APIView` handlers are synchronous; use plain Django async views, or django-ninja, when the endpoint must be `async`. Check the DRF docs for current async support before relying on it.

## 4. Authentication and permissions

- `SessionAuthentication` (cookie) enforces CSRF for unsafe methods; use it for same-site browser clients. `TokenAuthentication` (built in) and `BasicAuthentication` need HTTPS. For JWT or OAuth2 use a maintained package such as `djangorestframework-simplejwt` or `django-oauth-toolkit`, and check the current docs.
- Built-in permission classes: `AllowAny`, `IsAuthenticated`, `IsAdminUser`, `IsAuthenticatedOrReadOnly`, `DjangoModelPermissions`, `DjangoModelPermissionsOrAnonReadOnly`, `DjangoObjectPermissions`. Combine with `&`, `|` and `~`: `permission_classes = [IsAuthenticated & (IsAdminUser | IsOwner)]`.
- Object-level rule:

```python
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
```

- `has_permission` runs for every request; `has_object_permission` runs only when the view calls `get_object()`. List endpoints must filter in `get_queryset()`; the object check does not protect lists.
- The default `perms_map` of `DjangoModelPermissions` requires no permission for GET; override `perms_map` when reads must be restricted.
- Never rely on hiding a field in the UI. Enforce on the server in the serializer (`read_only`) and queryset.
- Token handling: tokens are credentials. Store hashed where the package allows it, support rotation and expiry, and never log `Authorization` headers. 3.18.2 fixed `TokenProxy` deletion so tokens delete properly.

## 5. Throttling

- Global: `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES` as in section 1. Rates are `number/period` with periods `second`, `minute`, `hour`, `day`.
- Per endpoint: `ScopedRateThrottle` with `throttle_scope` on the view or on an `@action`; add the scope names to `DEFAULT_THROTTLE_RATES`.
- Throttle state is stored in the Django cache. With several processes the cache must be shared (Redis or Memcached); `LocMemCache` gives each process its own counters.
- Behind a proxy set `NUM_PROXIES` in `REST_FRAMEWORK` (or configure the proxy to pass a trusted client address) so the client IP is derived correctly; otherwise all anonymous users may share one bucket or be spoofable through `X-Forwarded-For`.
- Throttle login and password-reset endpoints with a stricter scope. A rate limit is not a lockout; add monitoring.

## 6. Pagination and filtering

- `PageNumberPagination` (page and `page_size` query), `LimitOffsetPagination` (limit/offset), `CursorPagination` (opaque cursor, stable under inserts, needs an indexed ordering field). Prefer cursor for large or fast-changing tables.
- Cap client-controlled sizes: `max_page_size` (page number) and `max_limit` (limit/offset).
- Filtering with `django-filter` (`pip install django-filter`, add `"django_filters"` to `INSTALLED_APPS`) via `filter_backends = [DjangoFilterBackend]` and `filterset_fields`/`FilterSet`; `SearchFilter` and `OrderingFilter` ship with DRF. Whitelist `ordering_fields`.
- Filtering by user-controlled field names is a data-exposure risk; list them explicitly rather than allowing arbitrary lookups.

## 7. Errors and validation

- Validation failures return 400 with field-keyed lists of messages; permission failures 403 (401 when authentication is required and the authenticator supplies a `WWW-Authenticate` header); missing objects 404; throttled 429 with `Retry-After`.
- Customise the global error shape with `EXCEPTION_HANDLER` pointing at a function that calls `rest_framework.views.exception_handler` and reshapes `response.data`.
- Do not return `str(exception)` for unexpected errors; let Django log them and return a generic 500 body.
- `serializer.is_valid(raise_exception=True)` is the idiom in views; the handler turns it into a 400.
- Database errors that signal a race (`IntegrityError` on a unique constraint) should be caught around the write and mapped to 409 or 400.

## 8. Testing endpoints

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_list_and_restock(django_assert_num_queries):
    user = get_user_model().objects.create_superuser("x", "x@example.com", "pw")
    cat = Category.objects.create(name="a")
    product = Product.objects.create(category=cat, name="p", price_cents=5)
    client = APIClient()
    client.force_authenticate(user)

    with django_assert_num_queries(1):
        assert client.get("/api/products/").status_code == 200
    ok = client.post(f"/api/products/{product.pk}/restock/", {"amount": 5}, format="json")
    bad = client.post(f"/api/products/{product.pk}/restock/", {"amount": 0}, format="json")
    assert (ok.status_code, bad.status_code) == (204, 400)
    assert APIClient().post("/api/products/", {}, format="json").status_code in (401, 403)
```

- `force_authenticate` skips real auth; add at least one test through the real authentication class.
- Test anonymous, wrong-user, right-user and staff paths for each endpoint; test that foreign object ids return 404.
- Assert query counts for list endpoints with `django_assert_num_queries`.

## 9. Schema and docs

- DRF includes schema generation in `rest_framework.schemas`; check the DRF docs for the current status of the built-in generator. `drf-spectacular` is a widely used third-party generator (`pip install drf-spectacular`); check its docs for the current setup, including the `DEFAULT_SCHEMA_CLASS` setting.
- Publish the schema file in CI and diff it to catch breaking changes. Versioning policy and deprecation conventions: rest-api-expert.

## 10. django-ninja

django-ninja 1.7.3 (requires Django and Pydantic) builds APIs from type hints and Pydantic-style schemas, generates OpenAPI automatically and supports async handlers.

```python
from ninja import NinjaAPI, Router, Schema
from ninja.pagination import paginate

from .models import Product

api = NinjaAPI(title="Shop API", version="1")
router = Router()


class ProductOut(Schema):
    id: int
    name: str
    price_cents: int


class ProductIn(Schema):
    name: str
    price_cents: int
    category_id: int


@router.get("/products", response=list[ProductOut])
@paginate
def list_products(request):
    return Product.objects.all()


@router.post("/products", response={201: ProductOut})
def create_product(request, payload: ProductIn):
    return 201, Product.objects.create(**payload.dict())


api.add_router("", router)
# urls.py: path("api/", api.urls)
```

- Authentication is not on by default. Pass `auth=` to `NinjaAPI`, a router or an operation (for example a class from `ninja.security`), and test that anonymous calls are rejected.
- Choose DRF for large existing API surfaces, the permission class ecosystem, admin-like browsable tooling and team familiarity. Choose django-ninja for new, type-driven, OpenAPI-first services, or when async handlers matter. Do not mix both without a reason; both can coexist in one project under different URL prefixes.
- The ORM rules still apply: ninja serializes whatever the handler returns, so lazy relations in a response schema cause N+1 queries. Use `select_related` in the handler.
- For services that do not need Django (no ORM, admin or forms), use FastAPI (fastapi-expert).
