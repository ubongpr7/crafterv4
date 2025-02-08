from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.contrib import messages
from .models import TextFile


def check_credits_and_ownership(textfile_id_param, credits_required, deduct=False):
    """
    A decorator to check if a user has enough credits and if they own the TextFile.

    :param textfile_id_param: The name of the parameter in the view's kwargs that holds the TextFile ID.
    :param credits_required: The amount of credits required to access the view.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Extract the textfile_id from kwargs
            textfile_id = kwargs.get(textfile_id_param)
            textfile = get_object_or_404(TextFile, id=textfile_id)

            # Check if the logged-in user is the owner of the TextFile
            if textfile.user != request.user:
                messages.error(
                    request, "You do not have permission to access this file."
                )
                raise PermissionDenied(
                    "You do not have permission to access this file."
                )

            # Check if the user has an associated Credit object
            if request.user.subscription is None:
                messages.error(
                    request, "You need to subscribe to one of our plans to gain access."
                )
                return redirect(reverse("home:home") + "#pricing")

            # Check if the user has enough credits
            user_credits = request.user.subscription.credits
            if not request.user.is_superuser and user_credits <= 0:
            # if user_credits <= 0:
                # Redirect to pricing page with a relevant message
                messages.warning(
                    request,
                    "You do not have enough credits. Please subscribe to one of our plans.",
                )
                return redirect(reverse("home:home") + "#pricing")

            # If checks pass, call the original view
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def check_user_credits(minimum_credits_required):
    """
    Decorator to check if a user has enough credits to create a TextFile.
    Redirects to the pricing page if they don't have enough credits.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_superuser:
                user_sub = request.user.subscription
                if not user_sub or user_sub.credits < minimum_credits_required:
                    messages.error(
                        request,
                        "You don't have enough credits to create a new file. Please subscribe to any of our plans listed below.",
                    )
                    return redirect(reverse("home:home") + "#pricing")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
