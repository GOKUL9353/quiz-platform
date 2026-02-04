from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_choice, name='login_choice'),
    path('login/candidate/', views.candidate_login, name='candidate_login'),
    path('login/candidate/select-round/<int:event_id>/', views.select_round, name='select_round'),
    path('login/candidate/verify-round/<int:event_id>/<int:round_number>/', views.verify_round_login, name='verify_round_login'),
    path('login/admin/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('admin/panel/', views.admin_panel, name='admin_panel'),
    path('admin/add-event/', views.add_event, name='add_event'),
    path('admin/delete-event/', views.delete_event, name='delete_event'),
    path('admin/round-details/<int:event_id>/<int:round_number>/', views.round_details, name='round_details'),
    path('admin/add-question/<int:event_id>/<int:round_number>/', views.add_question, name='add_question'),
    
    # API endpoints
    path('api/verify-event-password/<int:event_id>/', views.verify_event_password, name='verify_event_password'),
    path('api/get-rounds/<int:event_id>/', views.get_rounds, name='get_rounds'),
    path('api/verify-round-password/<int:event_id>/<int:round_number>/', views.verify_round_password, name='verify_round_password'),
    path('api/submit-quiz/', views.submit_quiz, name='submit_quiz'),
    
    # Quiz test
    path('quiz-test/<int:event_id>/<int:round_number>/', views.quiz_test, name='quiz_test'),
]
