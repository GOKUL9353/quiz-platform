from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_choice, name='login_choice'),
    path('login/candidate/', views.candidate_login, name='candidate_login'),
    path('waiting-for-round/<int:event_id>/<int:round_number>/', views.waiting_for_round, name='waiting_for_round'),
    path('login/admin/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('admin/panel/', views.admin_panel, name='admin_panel'),
    path('admin/add-event/', views.add_event, name='add_event'),
    path('admin/delete-event/', views.delete_event, name='delete_event'),
    path('admin/round-details/<int:event_id>/<int:round_number>/', views.round_details, name='round_details'),
    path('admin/add-question/<int:event_id>/<int:round_number>/', views.add_question, name='add_question'),
    path('api/delete-question/<int:event_id>/<int:round_number>/<int:question_id>/', views.delete_question, name='delete_question'),
    path('admin/start-round/<int:event_id>/<int:round_number>/', views.start_round, name='start_round'),
    path('admin/end-round/<int:event_id>/<int:round_number>/', views.end_round, name='end_round'),
    
    # API endpoints
    path('api/verify-event-password/<int:event_id>/', views.verify_event_password, name='verify_event_password'),
    path('api/get-rounds/<int:event_id>/', views.get_rounds, name='get_rounds'),
    path('api/verify-round-password/<int:event_id>/<int:round_number>/', views.verify_round_password, name='verify_round_password'),
    path('api/submit-quiz/', views.submit_quiz, name='submit_quiz'),
    path('api/check-round-started/<int:event_id>/<int:round_number>/', views.check_round_started, name='check_round_started'),
    path('api/update-candidate-active/<int:candidate_entry_id>/', views.update_candidate_active, name='update_candidate_active'),
    path('api/exit-waiting/<int:candidate_entry_id>/', views.exit_waiting, name='exit_waiting'),
    path('api/init-waiting/<int:candidate_entry_id>/', views.init_waiting, name='init_waiting'),
    path('api/check-hosting-status/<int:event_id>/<int:round_number>/', views.check_hosting_status, name='check_hosting_status'),
    path('api/start-hosting/<int:event_id>/<int:round_number>/', views.api_start_hosting, name='api_start_hosting'),
    path('api/end-hosting/<int:event_id>/<int:round_number>/', views.api_end_hosting, name='api_end_hosting'),
    path('api/start-test/<int:event_id>/<int:round_number>/', views.api_start_test, name='api_start_test'),
    path('api/get-candidates/<int:event_id>/<int:round_number>/', views.api_get_candidates, name='api_get_candidates'),
    
    # Quiz test
    path('quiz-test/<int:event_id>/<int:round_number>/', views.quiz_test, name='quiz_test'),
]
