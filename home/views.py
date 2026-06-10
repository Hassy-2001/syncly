from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import authenticate,login,logout, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from allauth.socialaccount.adapter import get_adapter
from .models import *
from .forms import *
from .rate_limits import is_limited, limit_message

# Create your views here.

OAUTH_ROUTES = {
    'google': 'google_login',
    'github': 'github_login',
}

RATE_LIMITS = {
    'login': (5, 5 * 60),
    'register': (3, 60 * 60),
    'forgot_password': (3, 60 * 60),
    'resend_verification': (3, 60 * 60),
    'oauth': (20, 60 * 60),
    'create_room': (10, 60 * 60),
    'message': (20, 60),
    'upload': (10, 60 * 60),
    'reaction': (60, 60),
    'room_membership': (30, 60 * 60),
}


def _can_access_room(user, room):
    if not room.is_private:
        return True
    return user.is_authenticated and (user == room.host or room.participants.filter(id=user.id).exists())


def _visible_room_query(user):
    if user.is_authenticated:
        return Q(room__is_private=False) | Q(room__host=user) | Q(room__participants=user)
    return Q(room__is_private=False)


def _visible_messages(user):
    return (
        Message.objects
        .filter(_visible_room_query(user))
        .select_related('user', 'room', 'room__topic')
        .distinct()
    )


def _rate_limited(request, scope, identifiers=None):
    limit, window = RATE_LIMITS[scope]
    if is_limited(request, scope, limit, window, identifiers=identifiers):
        messages.error(request, limit_message(limit, window))
        return True
    return False


def _create_notification(recipient, actor, room, message, notification_type, text):
    if not recipient or not recipient.is_active or recipient == actor:
        return None

    notification, created = Notification.objects.get_or_create(
        recipient=recipient,
        actor=actor,
        room=room,
        message=message,
        notification_type=notification_type,
        defaults={'text': text},
    )
    if not created and notification.is_read:
        notification.is_read = False
        notification.text = text
        notification.created_at = timezone.now()
        notification.save(update_fields=['is_read', 'text', 'created_at'])
    return notification


def _notification_name(user):
    return user.first_name or user.email or user.username


def _upload_error_message(exc):
    reason = str(exc).strip()
    if not reason:
        return "We could not upload this file right now. Please check Cloudinary settings or try a smaller file."
    if len(reason) > 180:
        reason = f"{reason[:177]}..."
    return f"Upload failed: {reason}"


def _add_upload_save_error(form, exc, field_name='cover'):
    if field_name in form.fields:
        form.add_error(field_name, ValidationError(_upload_error_message(exc)))


def _notify_message_activity(message):
    actor = message.user
    room = message.room
    notified_ids = set()

    if message.parent and message.parent.user_id != actor.id:
        _create_notification(
            message.parent.user,
            actor,
            room,
            message,
            'reply',
            f"{_notification_name(actor)} replied to your message in {room.name}.",
        )
        notified_ids.add(message.parent.user_id)

    if room.host and room.host_id != actor.id and room.host_id not in notified_ids:
        _create_notification(
            room.host,
            actor,
            room,
            message,
            'room_message',
            f"{_notification_name(actor)} posted in your room {room.name}.",
        )
        notified_ids.add(room.host_id)

    body = (message.body or '').lower()
    room_users = User.objects.filter(
        Q(id=room.host_id) | Q(participants__id=room.id)
    ).distinct()
    for user in room_users:
        if user.id == actor.id or user.id in notified_ids:
            continue
        mention_tokens = [
            f"@{user.username}".lower(),
            (user.email or '').lower(),
            (user.first_name or '').lower(),
        ]
        if any(token and token in body for token in mention_tokens):
            _create_notification(
                user,
                actor,
                room,
                message,
                'mention',
                f"{_notification_name(actor)} mentioned you in {room.name}.",
            )
            notified_ids.add(user.id)


def _send_password_reset_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = request.build_absolute_uri(
        reverse('reset-password', kwargs={'uidb64': uidb64, 'token': token})
    )
    subject = 'Reset your Syncly password'
    message = (
        f"Hi {user.first_name or user.email or user.username},\n\n"
        "Click the link below to reset your Syncly password:\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'Syncly <no-reply@syncly.local>'),
        [user.email],
        fail_silently=False,
    )


def _send_email_verification_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('verify-email', kwargs={'uidb64': uidb64, 'token': token})
    )
    subject = 'Verify your Syncly email'
    message = (
        f"Hi {user.first_name or user.email or user.username},\n\n"
        "Click the link below to verify your Syncly account email:\n\n"
        f"{verify_url}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'Syncly <no-reply@syncly.local>'),
        [user.email],
        fail_silently=False,
    )


def loginUser(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == 'POST':
        identifier = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if _rate_limited(request, 'login', [identifier]):
            return render(request, 'base/login_register.html', {'page': page}, status=429)

        account = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier)).first()
        user = authenticate(request, username=account.username, password=password) if account else None

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Email or password is incorrect.")
    context = {'page': page}
    return render(request, 'base/login_register.html',context)        


def forgotPassword(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = ForgotPasswordRequestForm()
    if request.method == 'POST':
        form = ForgotPasswordRequestForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            if _rate_limited(request, 'forgot_password', [identifier]):
                return render(request, 'base/password_reset_request.html', {'form': form}, status=429)

            user = User.objects.filter(
                Q(email__iexact=identifier) | Q(username__iexact=identifier),
                is_active=True,
            ).first()

            if not user or not user.email:
                messages.error(request, "We could not find an active account with that email or username.")
                return render(request, 'base/password_reset_request.html', {'form': form})

            try:
                _send_password_reset_link(request, user)
            except Exception:
                messages.error(request, "We could not send the reset email right now. Please check email settings and try again.")
                return render(request, 'base/password_reset_request.html', {'form': form})

            messages.success(request, "We sent a password reset link to your email.")
            return redirect('login_user')

    return render(request, 'base/password_reset_request.html', {'form': form})


def resetPassword(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'base/password_reset_confirm.html', {
            'form': None,
            'invalid_link': True,
        })

    form = SetPasswordForm(user)
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password has been updated. You can log in now.")
            return redirect('login_user')

    return render(request, 'base/password_reset_confirm.html', {'form': form})

def registerUser(request):
    form = EmailUserCreationForm()
    if request.method == 'POST':
        form = EmailUserCreationForm(request.POST)
        email = request.POST.get('email', '').strip().lower()
        if _rate_limited(request, 'register', [email]):
            return render(request,"base/login_register.html", {"form" : form}, status=429)

        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            try:
                _send_email_verification_link(request, user)
                messages.success(request, "Account created. We sent a verification link to your email.")
            except Exception:
                messages.warning(request, "Account created, but we could not send the verification email right now.")
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("home")
        else:
            messages.error(request,"Please correct the highlighted fields.")
    context = {"form" : form}
    return render(request,"base/login_register.html",context)


def oauthLogin(request, provider):
    if _rate_limited(request, 'oauth', [provider]):
        return redirect("login_user")

    route_name = OAUTH_ROUTES.get(provider)
    if not route_name:
        messages.error(request, "That OAuth provider is not available.")
        return redirect("login_user")

    provider_apps = get_adapter(request).list_apps(request, provider=provider)
    if not provider_apps:
        provider_name = provider.title()
        messages.warning(
            request,
            f"{provider_name} login is ready, but its client ID and secret still need to be added in Django admin.",
        )
        return redirect("login_user")

    return redirect(route_name)


def logoutUser(request):
    logout(request)
    return redirect("home")


def verifyEmail(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This verification link is invalid or expired.")
        return redirect("login_user")

    profile, created = Profile.objects.get_or_create(user=user)
    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
    messages.success(request, "Your email has been verified.")
    return redirect("home")


@login_required(login_url="/login_user/")
def resendVerificationEmail(request):
    if _rate_limited(request, 'resend_verification'):
        return redirect("user-profile", pk=request.user.id)

    profile, created = Profile.objects.get_or_create(user=request.user)
    if profile.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("user-profile", pk=request.user.id)

    try:
        _send_email_verification_link(request, request.user)
        messages.success(request, "We sent a new verification link to your email.")
    except Exception:
        messages.error(request, "We could not send the verification email right now.")
    return redirect("user-profile", pk=request.user.id)


@login_required(login_url="/login_user/")
def changePassword(request):
    form = StyledPasswordChangeForm(request.user)
    if request.method == 'POST':
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed.")
            return redirect("user-profile", pk=request.user.id)
        messages.error(request, "Please correct the highlighted fields.")

    return render(request, 'base/change_password.html', {'form': form})


def userProfile(request, pk):
    user = get_object_or_404(User, id=pk)
    profile, created = Profile.objects.get_or_create(user=user)
    rooms = user.room_set.select_related('topic', 'host').prefetch_related('participants')
    if request.user != user:
        if request.user.is_authenticated:
            rooms = rooms.filter(Q(is_private=False) | Q(participants=request.user)).distinct()
        else:
            rooms = rooms.filter(is_private=False)
    room_messages = _visible_messages(request.user).filter(user=user)[:50]
    topics = Topic.objects.annotate(room_total=Count('room')).order_by('name')[:7]
    context = {
        "user": user,
        "profile": profile,
        "rooms": rooms[:30],
        "room_messages": room_messages,
        "topics": topics,
        "topic_count": Topic.objects.count(),
    }
    return render(request,'base/user_profile.html',context)

@login_required(login_url="/login_user/")
def update_profile(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    form = UserForm(instance=user)
    profile_form = ProfileForm(instance=profile)

    if request.method == 'POST':
          form = UserForm(request.POST, instance=user)
          profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
          if form.is_valid() and profile_form.is_valid():
            try:
                form.save()
                if request.POST.get('remove_photo') == 'on' and profile.photo:
                    profile.photo.delete(save=False)
                    profile.photo = None
                profile_form.save()
                return redirect("user-profile", pk=user.id)
            except Exception as exc:
                if request.FILES.get('photo'):
                    profile_form.add_error(
                        'photo',
                        ValidationError(
                            "We could not upload this profile photo right now. Please check Cloudinary settings or try a smaller image."
                        ),
                    )
                else:
                    messages.error(request, "We could not update your profile right now. Please try again.")
                print(f"Profile update failed for user {user.id}: {exc}")
    context = {"form": form, "profile_form": profile_form, "profile": profile}
    return render(request,'base/update_profile.html', context)

def home(request):
    query = (request.GET.get("query") or '').strip()[:120]
    rooms = (
        Room.objects
        .select_related('host', 'topic')
        .prefetch_related('participants')
        .filter(
            Q(topic__name__icontains=query) |
            Q(description__icontains=query) |
            Q(name__icontains=query)
        )
    )
    if request.user.is_authenticated:
        rooms = rooms.filter(Q(is_private=False) | Q(host=request.user) | Q(participants=request.user)).distinct()
    else:
        rooms = rooms.filter(is_private=False)
    room_count = rooms.count()
    rooms = rooms[:30]
    topic_count = Topic.objects.count()
    topics = Topic.objects.annotate(room_total=Count('room')).order_by('name')[:7]

    recent_messages = _visible_messages(request.user).filter(Q(room__topic__name__icontains=query))
    recent_update_count = recent_messages.count()
    room_messages = recent_messages[:12]
    context = {
        "rooms": rooms,
        'topics': topics,
        'topic_count': topic_count,
        'room_count': room_count,
        "room_messages": room_messages,
        "recent_update_count": recent_update_count,
    }
    return render(request,"base/home.html",context)


def topics(request):
    query = (request.GET.get("query") or '').strip()[:120]
    topics = Topic.objects.filter(name__icontains=query).annotate(room_total=Count('room')).order_by('name')
    context = {"topics": topics, "topic_count": topics.count()}
    return render(request,"base/topics.html", context)

def activity(request):
    room_messages = _visible_messages(request.user)[:80]
    context = {"room_messages": room_messages}
    return render(request,"base/activity.html", context)


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap'))
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /update_profile/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    urls = [
        request.build_absolute_uri(reverse('home')),
        request.build_absolute_uri(reverse('topics')),
        request.build_absolute_uri(reverse('activity')),
    ]
    public_rooms = Room.objects.filter(is_private=False).order_by('-updated_at').only('id', 'updated_at')[:100]
    for public_room in public_rooms:
        urls.append(request.build_absolute_uri(reverse('room', kwargs={'pk': public_room.id})))

    body = "\n".join(
        f"  <url><loc>{url}</loc></url>"
        for url in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>'
    return HttpResponse(xml, content_type="application/xml")

# CRUD Functionality for USER POST 

@login_required(login_url="/login_user/")
def create_room(request):
    form = RoomForm()
    if request.method == "POST":
        if _rate_limited(request, 'create_room'):
            return render(request,"base/room_form.html", {'form': form}, status=429)

        form = RoomForm(request.POST, request.FILES)
        if request.FILES and _rate_limited(request, 'upload'):
            return render(request,"base/room_form.html", {'form': form}, status=429)

        if form.is_valid():
            room = form.save(commit=False)
            room.host = request.user
            try:
                room.save()
                room.participants.add(request.user)
                return redirect("home")
            except Exception as exc:
                if request.FILES.get('cover'):
                    _add_upload_save_error(form, exc, 'cover')
                else:
                    messages.error(request, f"Room could not be saved: {str(exc)[:180]}")
                print(f"Room create failed for user {request.user.id}: {exc}")
    context = {'form': form}
    return render(request,"base/room_form.html",context)

def room(request, pk):
    room = get_object_or_404(
        Room.objects.select_related('host', 'topic').prefetch_related('participants'),
        id=pk,
    )
    if not _can_access_room(request.user, room):
        messages.warning(request, "This is a private room. Use an invite link to join.")
        return redirect("home")

    participants = room.participants.all()
    room_messages = (
        room.message_set
        .select_related('user', 'parent', 'parent__user')
        .prefetch_related('reactions')
        .order_by("-created_at")[:100]
    )

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login_user")
        if _rate_limited(request, 'message', [room.id]):
            return redirect("room", pk=room.id)

        form = MessageForm(request.POST, request.FILES)
        if request.FILES and _rate_limited(request, 'upload'):
            return redirect("room", pk=room.id)

        if form.is_valid():
            message = form.save(commit=False)
            message.user = request.user
            message.room = room
            parent_id = request.POST.get("parent")
            if parent_id:
                parent = Message.objects.filter(id=parent_id, room=room).first()
                if parent:
                    message.parent = parent
            try:
                message.save()
                room.participants.add(request.user)
                _notify_message_activity(message)
                return redirect("room", pk=room.id)
            except Exception as exc:
                if request.FILES.get('attachment'):
                    _add_upload_save_error(form, exc, 'attachment')
                else:
                    messages.error(request, f"Message could not be saved: {str(exc)[:180]}")
                print(f"Message save failed for user {request.user.id}: {exc}")
        messages.error(request, "Please write a message or attach a file.")

    is_participant = request.user.is_authenticated and room.participants.filter(id=request.user.id).exists()
    message_form = MessageForm()
    context = {"room": room, "room_messages": room_messages, "participants": participants, "is_participant": is_participant, "message_form": message_form}
    return render(request, "base/room.html", context)

@login_required(login_url="/login_user/")
def update_room(request, pk):
    room = get_object_or_404(Room, id=pk)
    form = RoomForm(instance=room)

    if request.user != room.host:
        return HttpResponseForbidden("You are not allowed to edit this room.")

    if request.method == "POST":
        if _rate_limited(request, 'create_room'):
            return render(request,"base/room_form.html", {'form': form}, status=429)

        form = RoomForm(request.POST, request.FILES, instance=room)
        if request.FILES and _rate_limited(request, 'upload'):
            return render(request,"base/room_form.html", {'form': form}, status=429)

        if form.is_valid():
            try:
                form.save()
                return redirect("home")
            except Exception as exc:
                if request.FILES.get('cover'):
                    _add_upload_save_error(form, exc, 'cover')
                else:
                    messages.error(request, f"Room could not be saved: {str(exc)[:180]}")
                print(f"Room update failed for user {request.user.id}: {exc}")
    context = {'form': form}
    return render(request,"base/room_form.html",context)


@login_required(login_url="/login_user/")
def delete_room(request, pk):
    room = get_object_or_404(Room, id=pk)

    if request.user != room.host:
        return HttpResponseForbidden("You are not allowed to delete this room.")
    
    if request.method == "POST":
            room.delete()
            return redirect("home")
    context = {'delete_room': room}
    return render(request,"base/delete.html",context)

@login_required(login_url="/login_user/")
def delete_message(request, pk):
    delete_message = get_object_or_404(Message, id=pk)
    if not _can_access_room(request.user, delete_message.room):
        return redirect("home")
    if request.user != delete_message.user:
        return HttpResponseForbidden("You are not allowed to delete this message.")
    
    if request.method == "POST":
            delete_message.delete()
            return redirect("home")
    context = {'delete_message': delete_message}
    return render(request,"base/delete.html",context)


@login_required(login_url="/login_user/")
def editMessage(request, pk):
    message = get_object_or_404(Message, id=pk)
    if request.user != message.user:
        return HttpResponseForbidden("You are not allowed to edit this message.")
    if not _can_access_room(request.user, message.room):
        return redirect("home")
    if _rate_limited(request, 'reaction', [message.id]):
        return redirect("room", pk=message.room.id)


    form = MessageForm(instance=message)
    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES, instance=message)
        if form.is_valid():
            edited = form.save(commit=False)
            edited.edited_at = timezone.now()
            try:
                edited.save()
                return redirect("room", pk=message.room.id)
            except Exception as exc:
                if request.FILES.get('attachment'):
                    _add_upload_save_error(form, exc, 'attachment')
                else:
                    messages.error(request, f"Message could not be saved: {str(exc)[:180]}")
                print(f"Message update failed for user {request.user.id}: {exc}")
        messages.error(request, "Please correct the highlighted fields.")

    return render(request, "base/message_form.html", {"form": form, "message": message})


@login_required(login_url="/login_user/")
@require_POST
def reactMessage(request, pk):
    message = get_object_or_404(Message, id=pk)
    if not _can_access_room(request.user, message.room):
        return redirect("home")
    if message.reactions.filter(id=request.user.id).exists():
        message.reactions.remove(request.user)
    else:
        message.reactions.add(request.user)
        _create_notification(
            message.user,
            request.user,
            message.room,
            message,
            'reaction',
            f"{_notification_name(request.user)} liked your message in {message.room.name}.",
        )
    return redirect("room", pk=message.room.id)


@login_required(login_url="/login_user/")
def notifications(request):
    user_notifications = request.user.notifications.select_related(
        'actor',
        'room',
        'message',
    )[:80]
    return render(request, "base/notifications.html", {"notifications": user_notifications})


@login_required(login_url="/login_user/")
def markNotificationRead(request, pk):
    notification = request.user.notifications.filter(id=pk).select_related('room').first()
    if not notification:
        return redirect("notifications")

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    if notification.room_id and _can_access_room(request.user, notification.room):
        return redirect("room", pk=notification.room_id)
    return redirect("notifications")


@login_required(login_url="/login_user/")
@require_POST
def markAllNotificationsRead(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")


@login_required(login_url="/login_user/")
@require_POST
def joinRoom(request, pk):
    room = get_object_or_404(Room, id=pk)
    if _rate_limited(request, 'room_membership', [room.id]):
        return redirect("home")

    if room.is_private:
        messages.warning(request, "Private rooms require an invite link.")
        return redirect("home")
    room.participants.add(request.user)
    messages.success(request, f"You joined {room.name}.")
    return redirect("room", pk=room.id)


@login_required(login_url="/login_user/")
@require_POST
def leaveRoom(request, pk):
    room = get_object_or_404(Room, id=pk)
    if _rate_limited(request, 'room_membership', [room.id]):
        return redirect("room", pk=room.id)

    if request.user == room.host:
        messages.warning(request, "Room hosts cannot leave their own room.")
        return redirect("room", pk=room.id)
    room.participants.remove(request.user)
    messages.success(request, f"You left {room.name}.")
    return redirect("home")


@login_required(login_url="/login_user/")
def joinRoomByInvite(request, invite_code):
    room = Room.objects.filter(invite_code=invite_code).first()
    if not room:
        messages.error(request, "That invite link is invalid.")
        return redirect("home")
    room.participants.add(request.user)
    messages.success(request, f"You joined {room.name}.")
    return redirect("room", pk=room.id)
