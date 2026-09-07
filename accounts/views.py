from django.contrib.auth.decorators import login_required
from annotation.models import Farm, Cow, Sequence, SequenceRating, Frame
from django.shortcuts import render
from django.http import JsonResponse
from .models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import logout,login,authenticate
from django.contrib import messages
from django.shortcuts import render , redirect ,get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Case, When, Value, IntegerField
    
def login_view(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(
            request,
            email=email,
            password=password
        )

        if user is None:
            messages.error(
                request,
                "No account found with this email or password."
            )
            return redirect("accounts:login")

        login(request, user)

        messages.success(
            request,
            f"Welcome back {user.email}"
        )

        return redirect("accounts:dashboard")

    return render(request, "accounts/login.html")
 

def register_view(request):

    if request.user.is_authenticated:
        return redirect('annotation:home')

    if request.method == 'POST':

        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()   
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Email validation
        if not email:
            messages.error(request, 'Please enter your email')
            return redirect('accounts:register')

        try:
            validate_email(email)
        except ValidationError as e:
            messages.error(request, " - ".join(e.messages))
            return redirect('accounts:register')

        if not first_name:
            messages.error(request, "Please enter your first name")
            return redirect("accounts:register")

        if not last_name:
            messages.error(request, "Please enter your last name")
            return redirect("accounts:register")
        # Password validation
        if not password:
            messages.error(request, 'Please enter your password')
            return redirect('accounts:register')

        if password != confirm_password:
            messages.error(
                request,
                'Password and confirmation do not match'
            )
            return redirect('accounts:register')

        try:

            user = User.objects.filter(email=email).first()

            # User exists
            if user:

                # Already verified
                if user.is_active:
                    messages.error(
                        request,
                        'This email is already registered'
                    )
                    return redirect('accounts:register')
                if  user.status == 'pending':
                    messages.error(
                        request,
                        'your request is already sumbmited'
                    )
                    return redirect('accounts:register')

                     

                     
                

               
                

            # Create new user
            if not user:

                try:
                    validate_password(password)

                except ValidationError as e:

                    messages.error(
                        request,
                        ", ".join(e.messages)
                    )

                    return redirect('accounts:register')

                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                    status="pending"
                )

                user.set_password(password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            send_mail(
                subject="New Registration Request",
                message=(
                    f"New registration request:\n\n"
                    f"Name: {user.get_full_name()}\n"
                    f"Email: {user.email}\n\n"
                    f"Review:\n"
                    f"https://hoofscore.iclassifier.ca/accounts/admin/pending_users_view/"
                ),

                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=False,
            )

            messages.success(
                request,
                'Your registration request has been submitted. Please wait for administrator approval'
            )

            return redirect('accounts:register')

        except Exception as e:

            print(f"Unexpected error: {e}")

            messages.error(
                request,
                'Failed to send registration request'
            )

            return redirect('accounts:register')

    return render(
        request,
        'accounts/register.html'
    )



@login_required(login_url="accounts:login")
def pending_users_view(request):

    if not request.user.is_admin:
        return redirect("annotation:home")

    users = (
        User.objects
        .exclude(role="admin")
        .annotate(
            status_order=Case(
                When(status="pending", then=Value(0)),
                When(status="approved", then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("status_order", "-created_at")
    )

    return render(
        request,
        "accounts/scoring_requests.html",
        {
            "users": users
        }
    )


@login_required
def set_scorer(request, user_id):

    if not request.user.is_admin:
        return redirect("annotation:home")

    user = get_object_or_404(
        User,
        id=user_id
    )
    if request.method == "POST":
        user.role = "scorer"
        user.is_active = True
        user.status = "approved"
        user.save(
                    update_fields=[
                        "role",
                        "is_active",
                        "status",
                    ]
                )

        send_mail(
            subject="HoofScore - Account Approved",
            message=(
                f"Hello {user.get_full_name()},\n\n"
                "Your registration request has been approved by the administrator.\n\n"
                "You can now sign in to the HoofScore platform using your registered email address and password.\n\n"
                "Login:\n"
                "https://hoofscore.iclassifier.ca/accounts/login/\n\n"
                "Thank you,\n"
                "HoofScore Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    return redirect(
        "accounts:scoring_requests"
    )

@login_required
def reject_user(request, user_id):

    if not request.user.is_admin:
        return redirect("annotation:home")

    user = get_object_or_404(
        User,
        id=user_id
    )

    send_mail(
        subject="Your registration request was declined",
        message=(
            f"Hello {user.get_full_name()},\n\n"
            "Unfortunately, your registration request has not been approved.\n\n"
            "If you believe this is a mistake, please contact the administrator."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )   
    user.delete()

    return redirect(
        "accounts:scoring_requests"
    )

@login_required
def set_tester(request, user_id):

    if not request.user.is_admin:
        return redirect("annotation:home")

    user = get_object_or_404(
        User,
        id=user_id
    )

    if request.method == "POST":
        user.role = "tester"
        user.save(update_fields=["role"])
        send_mail(
                    subject="HoofScore - Account Approved",
                    message=(
                        f"Hello {user.get_full_name()},\n\n"
                        "Your registration request has been approved as tester by the administrator.\n\n"
                        "You can now sign in to the HoofScore platform using your registered email address and password.\n\n"
                        "Login:\n"
                        "https://hoofscore.iclassifier.ca/accounts/login/\n\n"
                        "Thank you,\n"
                        "HoofScore Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
        
    return redirect("accounts:scoring_requests")


@login_required
def revoke_user(request, user_id):

    if not request.user.is_admin:
        return redirect("annotation:home")

    user = get_object_or_404(
        User,
        id=user_id
    )

    user.is_active = False
    user.status = "pending"
    user.role = ""

    user.save(
        update_fields=[
            "is_active",
            "status",
            "role",
        ]
    )

    return redirect(
        "accounts:scoring_requests"
    )






def logout_view(request):

    logout(request)
    return redirect('annotation:home')

def get_sequence_status(sequence):
    return "DONE" if sequence.ratings.exists() else "PENDING"


@login_required(login_url="accounts:login")
def dashboard_view(request):

    farms = Farm.objects.all()
    cows = Cow.objects.select_related("farm").all()

    completed_sequences = []

    for sequence in Sequence.objects.all():

        total_targets = (
            sequence.rating_targets
            .filter(annotations__isnull=False)
            .distinct()
            .count()
        )

        rated_targets = (
            SequenceRating.objects.filter(
                user=request.user,
                rating_target__sequence=sequence
            )
            .values("rating_target")
            .distinct()
            .count()
        )

        if total_targets == rated_targets:
            completed_sequences.append(sequence.id)

    rated_farms_count = (
        Farm.objects.filter(
            cows__sequences__id__in=completed_sequences
        )
        .distinct()
        .count()
    )

    context = {
        "farms_count": farms.count(),
        "cows_count": cows.count(),
        "rated_farms_count": rated_farms_count,
        "farms": farms,
        "cows": cows,
    }

    return render(request, "accounts/dashboard.html", context)



@login_required(login_url='accounts:login')
def profile_view(request):

    return render(
        request,
        'accounts/my_profile.html'
    )


@login_required(login_url='accounts:login')
def edit_profile_view(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        confirm_password = request.POST.get("confirm_password")

        if email != request.user.email:
            if request.user.__class__.objects.filter(email=email).exists():
                messages.error(
                    request,
                    "This email is already in use."
                )
                return redirect("edit_profile")

            request.user.email = email

        if password:

            if len(password) < 8:
                messages.error(
                    request,
                    "Password must be at least 8 characters long."
                )
                return redirect("accounts:edit_profile")

            if password != confirm_password:
                messages.error(
                    request,
                    "Passwords do not match."
                )
                return redirect("accounts:edit_profile")

            request.user.set_password(password)
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        messages.success(
            request,
            "Profile updated successfully."
        )

        return redirect("accounts:profile")

    return render(
        request,
        "accounts/edit_profile.html"
    )



