from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="signin"),
    path("logout/", views.logout_view, name="logout"),
    path("contact/", views.contact_view, name="contact"),
    path("verify/<str:token>", views.verify, name="verify"),
    path("stripe-webhook", views.stripe_webhook, name="stripe_webhook"),
    path("subscribe/<str:price_id>", views.subscribe, name="subscribe"),
    path("manage-subscription", views.manage_subscription, name="manage_subscription"),
    path(
        "upgrade-subscription/<str:price_id>",
        views.upgrade_subscription,
        name="upgrade_subscription",
    ),
    path(
        "downgrade-subscription",
        views.downgrade_subscription,
        name="downgrade_subscription",
    ),
    path("add-credits", views.add_credits, name="add_credits"),
    path("add-credits-success", views.add_credits_success, name="add_credits_success"),
    path("add-credits-cancel", views.add_credits_cancel, name="add_credits_cancel"),
    path("billing-portal", views.billing_portal, name="billing_portal"),
    path("cancel-subscription", views.cancel_subscription, name="cancel_subscription"),
]
