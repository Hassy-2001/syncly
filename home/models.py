from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid

# Create your models here.

class Topic(models.Model):
    name = models.CharField(max_length=200)
    
    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    email_verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} profile"

    @property
    def has_display_photo(self):
        return media_file_is_displayable(self.photo)

class Room(models.Model):
    host = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    topic = models.ForeignKey(Topic,on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank= True)
    cover = models.ImageField(upload_to='rooms/', null=True, blank=True)
    is_private = models.BooleanField(default=False)
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    participants = models.ManyToManyField(User, related_name="participants" , blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at','-created_at']

    def __str__(self):
        return self.name

    @property
    def has_display_cover(self):
        return media_file_is_displayable(self.cover)

class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room,on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    body = models.TextField()
    attachment = models.FileField(upload_to='messages/', null=True, blank=True)
    reactions = models.ManyToManyField(User, related_name='reacted_messages', blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.body[0:30]

    @property
    def has_display_attachment(self):
        return media_file_is_displayable(self.attachment)


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('reply', 'Reply'),
        ('room_message', 'Room message'),
        ('mention', 'Mention'),
        ('reaction', 'Reaction'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPES)
    text = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return self.text


def media_file_is_displayable(file_field):
    if not file_field:
        return False

    name = str(file_field.name or '')
    if not name:
        return False

    if not getattr(settings, 'MEDIA_UPLOADS_REQUIRE_CLOUDINARY', False):
        return True

    return name.startswith(('http://', 'https://')) or ':' in name
