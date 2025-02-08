from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout,
    get_user_model,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from mainapps.accounts.emails import send_html_email2
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import Plan, Subscription, StripeCustomer
import stripe
import uuid


@csrf_exempt
def contact_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        subject = f"New Contact Form Submission from {first_name} {last_name}"
        email_body = f"First Name: {first_name}\nLast Name: {last_name}\nEmail: {email}\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [
                    settings.DEFAULT_FROM_EMAIL,
                ],
            )
            return JsonResponse(
                {"success": True, "message": "Your message has been sent successfully!"}
            )
        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"An error occurred: {str(e)}"}
            )

    return JsonResponse({"success": False, "message": "Invalid request method."})


def logout_view(request):
    logout(request)

    # messages.success(request, "You Have Been Successfully Logged Out.")

    return redirect("/")


def login(request):
    if request.user.is_authenticated:
        return redirect("/text")

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.verification_token is None:
                auth_login(request, user)

                try:
                    return redirect(request.session.get("next"))
                except:
                    return redirect("/text")
            else:
                messages.error(
                    request,
                    "Your Email Address Is Not Verified. Please Verify Your Email Before Logging In.",
                )
        else:
            messages.error(request, "Invalid Username or Password. Please Try Again.")

    next = request.GET.get("next", "")
    request.session["next"] = next
    return render(
        request,
        "accounts/login.html",
    )


def register(request):
    if request.method == "POST":
        stripe.api_key = settings.STRIPE_SEC_KEY

        checkout_session_id = request.POST.get("session_id")

        name = request.POST.get("name")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if len(password1) < 6:
            messages.error(request, "At Least 6 Characters Are Required")
            return render(
                request,
                "accounts/register.html",
                context={"session_id": checkout_session_id},
            )

        if password1 != password2:
            messages.error(request, "Passwords Do Not Match.")
            return render(
                request,
                "accounts/register.html",
                context={"session_id": checkout_session_id},
            )

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            messages.error(request, "This Email Is Already Registered.")
            return render(
                request,
                "accounts/register.html",
                context={"session_id": checkout_session_id},
            )

        user = User.objects.create_user(email=email, password=password1)
        user.first_name = name
        user.save()

        if checkout_session_id is None:
            free_plan = Plan.objects.get(id=3)
            customer = stripe.Customer.create(
                email=user.email,
                name=user.first_name,
            )
            stripe_customer = StripeCustomer(user=user, stripe_customer_id=customer.id)
            stripe_customer.save()
            subscription = Subscription(
                plan=free_plan,
                credits=1,
                customer=stripe_customer,
                stripe_subscription_id=None,
            )
            subscription.save()
            user.subscription = subscription

            verification_token = str(uuid.uuid4())
            user.verification_token = verification_token

            user.save()

            send_html_email2(
                subject="Welcome to VideoCrafter.io – Verify Your Email To Continue",
                message=None,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_email=user.email,
                html_file="accounts/verification.html",
                context={
                    "first_name": user.first_name,
                    "verification_url": settings.DOMAIN_NAME
                    + reverse("accounts:verify", kwargs={"token": verification_token}),
                },
            )

            return render(
                request,
                "accounts/register.html",
                context={"price_id": "free", "success": True},
            )

        else:
            checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
            stripe_customer_id = checkout_session.customer
            subscription_id = checkout_session.get("subscription")
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                price_id = subscription["items"]["data"][0]["price"]["id"]
                print("Price ID:", price_id)
                customer_id = 0
                plan=Plan.objects.get(stripe_price_id=price_id)
                try:
                    customer = StripeCustomer.objects.get(
                        stripe_customer_id=stripe_customer_id
                    )

                    if customer is not None:
                        customer.user = user
                        customer.save()

                        customer_id = customer.id
                except StripeCustomer.DoesNotExist:
                    new_customer = StripeCustomer(
                        user=user, stripe_customer_id=stripe_customer_id
                    )
                    new_customer.save()

                    customer_id = new_customer.id

                try:

                    subscription = Subscription.objects.create(
                    plan=plan,
                    credits=plan.vsl_limit,
                    customer=new_customer,
                    stripe_subscription_id=subscription_id,
                    )   
                    user.subscription = subscription
                    user.save()

                except Exception as _:
                    messages.error(request, f"Subscription Failed. Please Try Again Later. {_}")
                    return redirect(f'/accounts/register/?session_id={checkout_session_id}'
                    )

            send_html_email2(
                subject="Welcome to VideoCrafter.io",
                message=None,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_email=user.email,
                html_file="accounts/welcome.html",
                context={
                    "user_name": user.first_name,
                    "login_url": settings.DOMAIN_NAME + reverse("video_text:add_text"),
                },
            )

            auth_login(request, user)
            return redirect(reverse("video_text:add_text"))
    
    elif request.method == "GET":
        checkout_session_id = request.GET.get("session_id")

        return render(
            request,
            "accounts/register.html",
            context={"session_id": checkout_session_id},
        )


def verify(request, token):
    try:
        user = get_user_model().objects.get(verification_token=token)

        if user is not None:
            user.verification_token = None
            user.save()

            auth_login(request, user)
            return redirect("video_text:add_text")
    except:
        return redirect(reverse("home:home"))


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SEC_KEY

    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]

    event = None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as _:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as _:
        return HttpResponse(status=400)

    event_type = event["type"]
    event_object = event["data"]["object"]

    if event_type == "invoice.payment_succeeded":
        if event_object.billing_reason == "subscription_create":
            try:
                customer_id = event_object.customer

                customer = None
                try:
                    customer = StripeCustomer.objects.get(
                        stripe_customer_id=customer_id
                    )
                except StripeCustomer.DoesNotExist:
                    customer = StripeCustomer(user=None, stripe_customer_id=customer_id)
                    customer.save()

                prev_sub = None
                prev_sub_credits = 0
                try:
                    prev_sub = Subscription.objects.get(customer_id=customer.id)

                    if prev_sub is not None:
                        if prev_sub.stripe_subscription_id is not None:
                            stripe.Subscription.delete(prev_sub.stripe_subscription_id)
                            prev_sub_credits = prev_sub.credits
                        elif prev_sub.credits > 1:
                            prev_sub_credits = prev_sub.credits
                except Subscription.DoesNotExist:
                    pass

                subscription_id = event_object.subscription
                price_id = event_object.lines.data[0].price.id
                plan = Plan.objects.get(stripe_price_id=price_id)
                subscription = Subscription(
                    plan=plan,
                    stripe_subscription_id=subscription_id,
                    customer=customer,
                    credits=plan.vsl_limit + prev_sub_credits,
                )
                subscription.save()

                if customer.user is not None:
                    customer.user.subscription = subscription
                    customer.user.save()

                    if prev_sub is not None:
                        prev_sub.delete()
            except Exception as e:
                print(
                    datetime.now().strftime("%H:%M:%S")
                    + f": Error in stripe webhook: {e}"
                )
        elif event_object.billing_reason == "subscription_cycle":
            try:
                price_id = event_object.lines.data[0].price.id
                plan = Plan.objects.get(stripe_price_id=price_id)

                subscription_id = event_object.subscription
                subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                subscription.credits = plan.vsl_limit + subscription.credits
                subscription.save()
            except Exception as e:
                print(
                    datetime.now().strftime("%H:%M:%S")
                    + f": Error in stripe webhook: {e}"
                )
    elif event_type == "invoice.payment_failed":
        if event_object.billing_reason == "subscription_create":
            messages.error(
                request,
                "Checkout error. Couldn't Complete Subsrciption Successfully. Please try again later.",
            )

            print(
                datetime.now().strftime("%H:%M:%S")
                + ": Payment Failed. Couldn't Complete Subsrciption Successfully. Please try again later."
            )
        elif event_object.billing_reason == "subscription_cycle":
            messages.error(
                request,
                "Checkout error. Couldn't Renew Subsrciption Successfully. Please try again later.",
            )

            print(
                datetime.now().strftime("%H:%M:%S")
                + ": Payment Failed. Couldn't Renew Subsrciption Successfully. Please try again later."
            )
    elif event_type == "customer.subscription.deleted":
        if event_object.cancel_at_period_end:
            customer_id = event_object.customer

            try:
                customer = StripeCustomer.objects.get(stripe_customer_id=customer_id)
            except StripeCustomer.DoesNotExist:
                return HttpResponse(status=404)

            sub = Subscription.objects.get(customer_id=customer.id)
            sub.credits = 0
            sub.save()

    return HttpResponse(status=200)


def subscribe(request, price_id):

    if request.method == "GET":
        user_url = request.GET.get("user_url")
        if user_url:
            request.session['user_url']=user_url
        try:
            stripe.api_key = settings.STRIPE_SEC_KEY

            success_path = request.GET.get("success_path")
            cancel_path = request.GET.get("cancel_path")

            customer = None
            if request.user.is_authenticated:
                customer = request.user.subscription.customer.stripe_customer_id

            checkout_session = stripe.checkout.Session.create(
                customer=customer,
                success_url=settings.DOMAIN_NAME
                + success_path
                + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=settings.DOMAIN_NAME + cancel_path,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
            )

            return redirect(checkout_session.url)
        except Exception as _:
            messages.error(request, "Checkout Error. Please Try Again Later.")
            return redirect(reverse("home:home"))



@login_required
def manage_subscription(request):
    user_url=request.session.get('user_url')
    
    if request.GET.get('session_id'):
        checkout_session_id = request.GET.get("session_id")
        if checkout_session_id and request.user.is_authenticated:
            user= request.user
            
            checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
            stripe_customer_id = checkout_session.customer
            checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
            stripe_customer_id = checkout_session.customer
            subscription_id = checkout_session.get("subscription")
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                price_id = subscription["items"]["data"][0]["price"]["id"]
                print("Price ID:", price_id)
                customer_id = 0
                plan=Plan.objects.get(stripe_price_id=price_id)
                try:
                    customer = StripeCustomer.objects.get(
                        stripe_customer_id=stripe_customer_id
                    )

                    if customer is not None:
                        customer.user = user
                        customer.save()

                        customer_id = customer.id
                except StripeCustomer.DoesNotExist:
                    new_customer = StripeCustomer(
                        user=user, stripe_customer_id=stripe_customer_id
                    )
                    new_customer.save()
                    customer=new_customer
                    customer_id = new_customer.id
                

                try:
                    try:

                        subscription = Subscription.objects.create(
                        plan=plan,
                        credits=plan.vsl_limit +user.subscription.credits,
                        customer=customer,
                        stripe_subscription_id=subscription_id,
                        )   
                    except Exception as e:
                        subscription = Subscription.objects.create(
                        plan=plan,
                        credits=plan.vsl_limit,
                        customer=customer,
                        stripe_subscription_id=subscription_id,
                        )   
                    user.subscription = subscription
                    user.save()

            
                except Exception as e:
                    print(e)
                    logout(request)
                    return redirect('/')

    if user_url:
        request.session['user_url']=None
        return redirect(user_url)
    credits_left = request.user.subscription.credits
    total_credits = max(request.user.subscription.plan.vsl_limit, credits_left)

    current_period_end = 0
    if request.user.subscription.stripe_subscription_id is not None:
        stripe.api_key = settings.STRIPE_SEC_KEY

        subscription = stripe.Subscription.retrieve(
            request.user.subscription.stripe_subscription_id
        )

        current_period_end = int(subscription["current_period_end"])
    else:
        current_period_end = request.user.subscription.current_period_end

    now = int(datetime.now().timestamp())
    days_left = int((current_period_end - now) / 60 / 60 / 24)
    days_left = max(-1, days_left)
    days_left += 1

    return render(
        request,
        "accounts/details.html",
        context={
            "total_credits": total_credits,
            "credits_left": credits_left,
            "cur_plan": request.user.subscription.plan,
            "plans": Plan.objects.all(),
            "days_left": days_left,
        },
    )

@login_required
def upgrade_subscription(request, price_id):
    return subscribe(request, price_id)


@login_required
def downgrade_subscription(request):
    try:
        if request.user.subscription.plan.id == 2:
            subscription = stripe.Subscription.retrieve(
                request.user.subscription.stripe_subscription_id
            )

            stripe.Subscription.modify(
                subscription.id,
                items=[
                    {
                        "id": subscription["items"]["data"][0].id,
                        "price": settings.GROWTH_PLAN_PRICE_ID,
                    }
                ],
                proration_behavior="none",
            )

            growth_plan = Plan.objects.get(id=1)
            request.user.subscription.plan = growth_plan
            request.user.subscription.save()

            messages.success(request, "Downgraded To Growth Plan Successfully.")
            return redirect(reverse("accounts:manage_subscription"))
    except Exception as e:
        messages.error(request, f"Downgrading Failed. Please Try Again Later. {e}")
        return redirect(reverse("accounts:manage_subscription"))


@login_required
def add_credits(request):
    if request.method == "POST":
        if (
            int(request.POST.get("credits_number")) >= 1
            and request.user.subscription.plan.name.lower() != "free"
        ):
            try:
                stripe.api_key = settings.STRIPE_SEC_KEY

                checkout_session = stripe.checkout.Session.create(
                    customer=request.user.subscription.customer.stripe_customer_id,
                    success_url=settings.DOMAIN_NAME
                    + reverse("accounts:add_credits_success")
                    + f'?amount={request.POST.get("credits_number")}',
                    cancel_url=settings.DOMAIN_NAME
                    + reverse("accounts:add_credits_cancel"),
                    payment_method_types=["card"],
                    line_items=[
                        {
                            "price_data": {
                                "currency": "usd",
                                "product_data": {
                                    "name": f'{request.POST.get("credits_number")} Credits',
                                },
                                "unit_amount": int(
                                    float(request.user.subscription.plan.price_per_vsl)
                                    * 100
                                ),
                            },
                            "quantity": int(request.POST.get("credits_number")),
                        },
                    ],
                    mode="payment",
                )

                return redirect(checkout_session.url)
            except Exception as _:
                messages.error(request, "Checkout Error. Please Try Again Later.")
                return redirect(reverse("home:home"))


@login_required
def add_credits_success(request):
    if request.method == "GET":
        new_credits = int(request.GET.get("amount"))
        request.user.subscription.credits += new_credits
        request.user.subscription.save()
        messages.success(request, "Extra Credits Added To Your Account Successfully")
        return redirect(reverse("accounts:manage_subscription"))


def add_credits_cancel(request):
    messages.error(request, "Adding Extra Credits Cancelled")
    return redirect(reverse("accounts:manage_subscription"))


@login_required
def billing_portal(request):
    stripe.api_key = settings.STRIPE_SEC_KEY

    try:
        customer = StripeCustomer.objects.get(user_id=request.user.id)

        session = stripe.billing_portal.Session.create(
            customer=customer.stripe_customer_id,
            return_url=settings.DOMAIN_NAME + reverse("home:home"),
        )

        return redirect(session.url)
    except Exception as _:
        messages.error(request, "An Error Occurred. Please try again later.")
        return redirect(reverse("home:home"))


@login_required
def cancel_subscription(request):
    stripe.api_key = settings.STRIPE_SEC_KEY

    try:
        subscription = stripe.Subscription.retrieve(
            request.user.subscription.stripe_subscription_id
        )
        stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True,
        )

        cancelled_plan = Plan.objects.get(id=5)
        request.user.subscription.plan = cancelled_plan
        request.user.subscription.stripe_subscription_id = None
        request.user.subscription.current_period_end = subscription.current_period_end
        request.user.subscription.save()

        messages.success(request, "Subscription Cancelled Successfully")
        return redirect(reverse("accounts:manage_subscription"))
    except Exception as _:
        print(_)
        messages.error(
            request, "Something Went Wrong. Couldn't Cancel Your Subscription."
        )
        return redirect(reverse("accounts:manage_subscription"))
