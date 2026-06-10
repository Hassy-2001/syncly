from django.urls import path
from .import views

urlpatterns = [
    path("",views.home, name="home"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("room/<str:pk>/",views.room, name="room"),


    path("register_user/",views.registerUser, name="register_user"),
    path("login_user/",views.loginUser, name="login_user"),
    path("forgot-password/", views.forgotPassword, name="forgot-password"),
    path("reset-password/<uidb64>/<token>/", views.resetPassword, name="reset-password"),
    path("verify-email/<uidb64>/<token>/", views.verifyEmail, name="verify-email"),
    path("resend-verification/", views.resendVerificationEmail, name="resend-verification"),
    path("change-password/", views.changePassword, name="change-password"),
    path("oauth/<str:provider>/", views.oauthLogin, name="oauth-login"),
    path("logout_user/",views.logoutUser, name="logout_user"),
    path("user_profile/<str:pk>/",views.userProfile, name="user-profile"),
    path("update_profile/",views.update_profile, name="update-profile"),
    path("topics/",views.topics, name="topics"),
    path("activity/",views.activity, name="activity"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<str:pk>/read/", views.markNotificationRead, name="notification-read"),
    path("notifications/read-all/", views.markAllNotificationsRead, name="notifications-read-all"),

    path("create-room/",views.create_room, name="create-room"),
    path("join-room/<str:pk>/", views.joinRoom, name="join-room"),
    path("leave-room/<str:pk>/", views.leaveRoom, name="leave-room"),
    path("invite/<uuid:invite_code>/", views.joinRoomByInvite, name="room-invite"),
    path("update-room/<str:pk>/",views.update_room, name="update-room"),
    path("delete-room/<str:pk>/",views.delete_room, name="delete-room"),
    path("edit-message/<str:pk>/", views.editMessage, name="edit-message"),
    path("react-message/<str:pk>/", views.reactMessage, name="react-message"),
    path("delete-message/<str:pk>/",views.delete_message, name="delete-message"),

]
