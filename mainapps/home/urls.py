from django.urls import path
from . import views

app_name = "home"
urlpatterns = [
    path("", views.home, name="home"),
    path("terms-and-conditions/", views.terms_and_conditions, name="terms_conditions"),
    path("privacy-policy/", views.privacy_and_policy, name="privacy_policy"),
    path("refund-policy/", views.refund_and_policy, name="refund_policy"),
    path("affiliate-terms/", views.affiliate_programs_terms, name="affiliate_terms"),
]
