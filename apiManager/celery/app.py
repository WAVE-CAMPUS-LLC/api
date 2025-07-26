import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab


celery_app = Celery("wave", broker=settings.REDIS_URL)
celery_app.conf.update(
    result_backend=settings.REDIS_URL,
    timezone=settings.TIME_ZONE,
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)


celery_app.autodiscover_tasks(
    [
        "apiManager.apps.accountManagementAPI.tasks",
        "apiManager.apps.adminManagementAPI.tasks",
        "apiManager.apps.ambassadorManagementAPI.tasks",
        "apiManager.apps.authenticationAPI.tasks",
        "apiManager.apps.collegeManagementAPI.tasks",
        "apiManager.apps.coreAPI.tasks",
        "apiManager.apps.eventManagementAPI.tasks",
        "apiManager.apps.eventTicketsAPI.tasks",
        "apiManager.apps.newsroomAPI.tasks",
        "apiManager.apps.notificationsManagementAPI.tasks",
        "apiManager.apps.socialAPI.tasks",
        "apiManager.apps.tracingAPI.tasks",
        "apiManager.apps.walleManagementAPI.tasks",
    ]
)

celery_app.conf.beat_schedule = {
    "send-daily-mood-prompts": {
        "task": "apiManager.apps.coreAPI.tasks.send_daily_mood_prompts",
        "schedule": crontab(hour=13, minute=25),  # Every day at 8 AM
    },
}
