from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from mainapps.accounts.emails import (
    CustomPasswordResetConfirmView,
    CustomPasswordResetView,
)

urlpatterns = [
    path("", include("mainapps.home.urls", namespace="home")),
    path("admin/", admin.site.urls),
    path("accounts/", include("mainapps.accounts.urls", namespace="accounts")),
    path("video/", include("mainapps.video.urls", namespace="video")),
    path("text/", include("mainapps.vidoe_text.urls", namespace="video_text")),
    path(
        "auth/password_reset/", CustomPasswordResetView.as_view(), name="password_reset"
    ),
    path(
        "auth/reset/<uidb64>/<token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("auth/", include("django.contrib.auth.urls")),  # new
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
