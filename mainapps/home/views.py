from django.shortcuts import redirect, render
from django.conf import settings


def home(request):
    price_ids = {
        "growth": settings.GROWTH_PLAN_PRICE_ID,
        "pro": settings.PRO_PLAN_PRICE_ID,
    }

    if request.user.is_authenticated:
        if request.user.subscription and request.user.subscription.credits >= 1:
            return redirect("/text")
        else:
            return render(
                request, "vlc/frontend/landing.html", context={"price_ids": price_ids}
            )
    else:
        return render(
            request, "vlc/frontend/landing.html", context={"price_ids": price_ids}
        )



def terms_and_conditions(request):

    return render(
        request, "vlc/frontend/terms-conditions.html", context={}
    )


def privacy_and_policy(request):

    return render(
        request, "vlc/frontend/privacy-policy.html", context={}
    )

def refund_and_policy(request):

    return render(
        request, "vlc/frontend/refund-policy.html", context={}
    )



def affiliate_programs_terms(request):

    return render(
        request, "vlc/frontend/affiliate-terms.html", context={}
    )