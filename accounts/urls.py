from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/",views.profile_view,name="profile"),
    path("profile/edit/",views.edit_profile_view,name="edit_profile"),
    path("logout/", views.logout_view, name="logout"),
   
    path("admin/pending_users_view/", views.pending_users_view, name="scoring_requests"),
    path("admin/reject_user/<int:user_id>/", views.reject_user, name="reject_scoring_request"),
    path("admin/revoke_user/<int:user_id>/", views.revoke_user, name="revoke_scoring_request"),
    path(
        "users/<int:user_id>/set-scorer/",
        views.set_scorer,
        name="set_scorer"
    ),

    path(
        "users/<int:user_id>/set-tester/",
        views.set_tester,
        name="set_tester"
    ),

]