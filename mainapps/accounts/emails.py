import threading
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.views import PasswordResetView
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import login
from django.contrib.auth.views import PasswordResetConfirmView
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class EmailThread(threading.Thread):
    def __init__(self, email_message):
        self.email_message = email_message
        threading.Thread.__init__(self)

    def run(self):
        print("Initializing thread")
        self.email_message.send()
        if self.email_message.send():
            print("Email sent successfully")


def send_html_email2(subject, message, from_email, to_email, html_file, context):
    html_content = render_to_string(html_file, context)

    text_content = strip_tags(html_content)

    send_mail(subject, text_content, from_email, [to_email], html_message=html_content)


def send_html_email(subject, message, from_email, to_email, html_file, context):
    html_content = render_to_string(html_file, context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    EmailThread(msg).start()


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = "/text"

    def form_valid(self, form):
        response = super().form_valid(form)

        user = form.user
        login(self.request, user)

        return redirect(self.success_url)


class CustomPasswordResetView(PasswordResetView):
    html_email_template_name = "registration/password_reset_email.html"

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
        use_django_email=True,
    ):
        subject = render_to_string(subject_template_name, context).strip()
        html_file = html_email_template_name or self.html_email_template_name

        send_html_email(
            subject=subject,
            message=None,
            from_email=from_email,
            to_email=to_email,
            html_file=html_file,
            context=context,
        )
