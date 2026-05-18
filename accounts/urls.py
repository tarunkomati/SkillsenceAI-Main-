from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile-update'),
    path('staff/approvals/', views.approval_requests_view, name='staff-approvals'),
    path('staff/approvals/<int:user_id>/', views.approval_request_action_view, name='staff-approvals-action'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('recalculate/', views.recalculate_scores_view, name='recalculate-scores'),
    path('score-report/', views.score_report_view, name='score-report'),
]
