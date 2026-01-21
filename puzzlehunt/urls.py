from django.urls import path, register_converter
from django.conf.urls import include
from puzzlehunt import info_views, hunt_views, staff_views
from django_eventstream.views import events
from puzzlehunt.utils import HuntConverter, FallbackHuntConverter
from django.views.generic.base import RedirectView

app_name = 'puzzlehunt'

register_converter(HuntConverter, 'hunt')
register_converter(FallbackHuntConverter, 'hunt-fallback')


urlpatterns = [
    # General Pages
    path('', info_views.index, name='index'),
    path('archive/', info_views.archive, name='archive'),
    path('info/', include('django.contrib.flatpages.urls')),
    path('protected/trusted/<str:base>/<str:pk>/<path:file_path>', hunt_views.protected_static, name='protected_static_generic'),
    path('protected/<str:base>/<str:pk>/<path:file_path>', hunt_views.protected_static, name='protected_static_generic'),

    # User / Teams
    path('user/detail', info_views.user_detail_view, name='user_detail_view'),
    path('team/<str:pk>/view/', info_views.team_view, name='team_view'),
    path('team/<str:pk>/update/', info_views.team_update, name='team_update'),
    path('team/<str:pk>/leave/', info_views.team_leave, name='team_leave'),
    path('team/<str:pk>/join/', info_views.team_join, name='team_join'),
    path('team/join/', info_views.team_join, name='team_join_current'),
    path('team/create/', info_views.team_create, name='team_create'),

    # Puzzles
    path('puzzle/<str:pk>/', RedirectView.as_view(pattern_name='puzzlehunt:puzzle_view', permanent=True), name='puzzle_view_redirect'),
    path('puzzle/<str:pk>/view/', hunt_views.puzzle_view, name='puzzle_view'),
    path('puzzle/<str:pk>/view/<path:file_path>', hunt_views.protected_static,
         {"base": "puzzle", "add_prefix": True}, name='protected_static_puzzle'),
    path('puzzle/<str:pk>/submit/', hunt_views.puzzle_submit, name='puzzle_submit'),
    path('puzzle/<str:pk>/solution/', hunt_views.puzzle_solution, name='puzzle_solution'),
    path('puzzle/<str:pk>/solution/<path:file_path>', hunt_views.protected_static,
         {"base": "solution", "add_prefix": True}, name='protected_static_solution'),
    path('puzzle/<str:pk>/hints/view/', hunt_views.puzzle_hints_view, name='puzzle_hints_view'),
    path('puzzle/<str:pk>/hints/submit/', hunt_views.puzzle_hints_submit, name='puzzle_hints_submit'),
    path('puzzle/<str:pk>/hints/canned/', hunt_views.puzzle_hints_use_canned, name='puzzle_hints_use_canned'),

    # Hunts
    path('hunt/<hunt:hunt>/', RedirectView.as_view(pattern_name='puzzlehunt:hunt_view', permanent=True), name='hunt_view_redirect'),
    path('hunt/<hunt:hunt>/view/', hunt_views.hunt_view, name='hunt_view'),
    path('hunt/<str:pk>/view/<path:file_path>', hunt_views.protected_static,
         {"base": "hunt", "add_prefix": True}, name='protected_static_hunt'),
    path('hunt/<hunt:hunt>/leaderboard/', hunt_views.hunt_leaderboard, name='hunt_leaderboard'),
    path('hunt/<hunt:hunt>/updates/', hunt_views.hunt_updates, name='hunt_updates'),
    path('hunt/<hunt:hunt>/prepuzzle/', hunt_views.hunt_prepuzzle, name='hunt_prepuzzle'),
    path('hunt/<hunt:hunt>/info/', hunt_views.hunt_info, name='hunt_info'),

    # Prepuzzles
    path('prepuzzle/<int:pk>/view/', hunt_views.prepuzzle_view, name='prepuzzle_view'),
    path('prepuzzle/<int:pk>/submit/', hunt_views.prepuzzle_submit, name='prepuzzle_submit'),
    # Legacy route for old prepuzzles
    path('prepuzzle/<int:pk>/check/', hunt_views.prepuzzle_check, name='prepuzzle_check'),

    # SSE Endpoints
    path('sse/team/<str:pk>/', events, {'format-channels': ['team-{pk}']}, name='team_events'),
    path('sse/staff/', events, {'channels': ['staff']}, name='staff_events'),


    # Staff Pages
    path('staff/', include(([
        path("", staff_views.staff_base, name="index"),

        # Are based on hint pks, don't need a hunt prefix
        path('hint/<int:pk>/claim/', staff_views.hints_claim, name='hints_claim'),
        path('hint/<int:pk>/release/', staff_views.hints_release, name='hints_release'),
        path('hint/<int:pk>/respond/', staff_views.hints_respond, name='hints_respond'),
        path('hint/<int:pk>/refund/', staff_views.hints_refund, name='hints_refund'),
        path('hint/<int:pk>/get_modal/', staff_views.get_modal, name='get_modal'),

        # These already take a hunt argument
        path('hunt/<hunt-fallback:hunt>/search/', staff_views.search, name='search'),
        path('hunt/<hunt-fallback:hunt>/hunts/', staff_views.view_hunts, name='hunts'),
        path('hunt/<hunt-fallback:hunt>/feed/', staff_views.feed, name='feed'),
        path('hunt/<hunt-fallback:hunt>/progress/', staff_views.progress, name='progress'),
        path('hunt/<hunt-fallback:hunt>/progress_data/', staff_views.progress_data, name='progress_data'),
        path('hunt/<hunt-fallback:hunt>/hints/', staff_views.hints_view, name='hints_view'),
        path('hunt/<hunt-fallback:hunt>/charts/', staff_views.charts, name='charts'),
        path('hunt/<hunt-fallback:hunt>/participant_info/', staff_views.participant_info, name='participant_info'),
        path('hunt/<hunt-fallback:hunt>/download-emails/', staff_views.download_emails, name='download_emails'),
        path('hunt/<hunt-fallback:hunt>/template/', staff_views.hunt_template, name='hunt_template'),
        path('hunt/<hunt-fallback:hunt>/template/preview/', staff_views.preview_template, name='preview_template'),
        path('hunt/<hunt-fallback:hunt>/config/', staff_views.hunt_config, name='hunt_config'),
        path('hunt/<hunt-fallback:hunt>/config-tester/', staff_views.config_tester, name='config_tester'),
        path('hunt/<hunt-fallback:hunt>/puzzles/', staff_views.hunt_puzzles, name='hunt_puzzles'),
        path('hunt/<hunt-fallback:hunt>/set_current/', staff_views.hunt_set_current, name='hunt_set_current'),
        path('hunt/<hunt-fallback:hunt>/export/', staff_views.export_hunt, name='hunt_export'),
        path('hunt/<hunt-fallback:hunt>/import/', staff_views.import_hunt, name='hunt_import'),
        path('hunt/<hunt-fallback:hunt>/reset/', staff_views.hunt_reset, name='hunt_reset'),

        path('hunt/<hunt-fallback:hunt>/file-editor/', staff_views.file_editor, name='file_editor'),
        path('file-editor/puzzle-list/', staff_views.file_editor_puzzle_list, name='file_editor_puzzle_list'),
        path('file-editor/file-list/', staff_views.file_editor_file_list, name='file_editor_file_list'),
        path('file-editor/load-content/', staff_views.file_editor_load_content, name='file_editor_load_content'),
        path('file/<str:parent_type>/<int:pk>/save/', staff_views.file_save_content, name='file_save_content'),

        path('<str:parent_type>/file/<str:pk>/delete/', staff_views.file_delete, name='file_delete'),
        path('<str:parent_type>/file/<str:pk>/replace/', staff_views.file_replace, name='file_replace'),
        path('<str:parent_type>/file/<str:pk>/download/', staff_views.file_download, name='file_download'),
        path('<str:parent_type>/file/<str:pk>/set_main/', staff_views.file_set_main, name='file_set_main'),
        path('<str:parent_type>/<str:pk>/files/delete_all/', staff_views.file_delete_all, name='file_delete_all'),
        path('<str:parent_type>/<str:pk>/files/upload/', staff_views.file_upload, name='file_upload'),
    ], 'staff'), namespace='staff')),

    # Notification management URLs
    path('notifications/', info_views.notification_view, name='notification_view'),
    path('notifications/<int:pk>/delete/', info_views.notification_delete, name='notification_delete'),
    path('notifications/<int:pk>/toggle/', info_views.notification_toggle, name='notification_toggle'),
]


