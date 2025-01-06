from django.db.models import Count, Max, Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncHour
from django.http import JsonResponse
from datetime import timedelta
from django.utils.timezone import now, datetime
from django.utils.formats import date_format
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt 

import json

from dataAnalyticsAPI.models import  GuestUser, InteractiveEventControl
from authenticationApp.models import CustomUser
from accountManagementApp.models import UserProfile
from adminDashboardApp.models import LoginHistoryModel
from adminDashboardApp.models import College
from collegeManagementApp.models import Membership, Organization, OrganizationMembership
from eventManagementApp.models import Event


# User Analytics API
def userSignups(request):
    period = request.GET.get("period", "daily")  # Default to daily if not provided

    if period == "monthly":
        # Get signups grouped by month and count the number of signups per month
        signups = (
            CustomUser.objects.annotate(month=TruncMonth("date_joined"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        # Prepare data for the chart
        labels = [
            signup["month"].strftime("%B %Y") for signup in signups
        ]  # Format month as "January 2024"
        counts = [signup["count"] for signup in signups]

    elif period == "weekly":
        # Get signups grouped by week (similar to the monthly grouping logic)
        signups = (
            CustomUser.objects.annotate(week=TruncWeek("date_joined"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )

        labels = [
            f"Week of {signup['week'].strftime('%d %b %Y')}" for signup in signups
        ]
        counts = [signup["count"] for signup in signups]

    else:  # Daily
        # Get daily signups
        signups = (
            CustomUser.objects.annotate(day=TruncDay("date_joined"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        labels = [signup["day"].strftime("%Y-%m-%d") for signup in signups]
        counts = [signup["count"] for signup in signups]

    return JsonResponse({"labels": labels, "counts": counts})


def userLogins(request):
    trend_type = request.GET.get("trend", "general")  # Default trend: general

    if trend_type == "general":
        data = {
            "total_logins": LoginHistoryModel.objects.count(),
            "unique_users": LoginHistoryModel.objects.values("user").distinct().count(),
            "active_sessions": LoginHistoryModel.objects.filter(
                logout_time__isnull=True
            ).count(),
            "average_session_duration": LoginHistoryModel.objects.aggregate(
                avg_duration=Avg(
                    F("session_duration_minutes") + F("session_duration_seconds") / 60
                )
            )["avg_duration"]
            or 0,
        }

    elif trend_type == "user_activity":
        data = list(
            LoginHistoryModel.objects.values("user__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]  # Top 10 users
        )

    elif trend_type == "time_trends":
        time_frame = request.GET.get("time_frame", "hourly")
        trunc_function = {
            "hourly": TruncHour,
            "daily": TruncDay,
            "monthly": TruncMonth,
        }.get(time_frame, TruncHour)

        data = list(
            LoginHistoryModel.objects.annotate(time_period=trunc_function("login_time"))
            .values("time_period")
            .annotate(count=Count("id"))
            .order_by("time_period")
        )

    elif trend_type == "ip_insights":
        data = list(
            LoginHistoryModel.objects.values("ip_address")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]  # Top 10 IP addresses
        )

    elif trend_type == "security":
        data = {}

        # Track failed login attempts for users who are not in any group
        data["failed_login_attempts"] = LoginHistoryModel.objects.filter(
            user__groups__isnull=True  # Users who are not in any group
        ).count()

        # Track active sessions with users not in any group
        data["active_sessions_with_no_groups"] = LoginHistoryModel.objects.filter(
            logout_time__isnull=True,  # Active sessions
            user__groups__isnull=True,  # Users not in any group
        ).count()

        # Track failed login attempts for users in each group
        group_data = (
            LoginHistoryModel.objects.filter(
                role__isnull=True  # You can keep role filtering or remove this as per your logic
            )
            .values("user__groups__name")
            .annotate(failed_attempts=Count("id"))
            .order_by("-failed_attempts")
        )

        # Convert queryset to list
        data["failed_login_attempts_by_group"] = list(group_data)

        # Track active sessions grouped by the groups
        active_sessions_by_group = (
            LoginHistoryModel.objects.filter(
                logout_time__isnull=True  # Active sessions
            )
            .values("user__groups__name")
            .annotate(active_sessions=Count("id"))
            .order_by("-active_sessions")
        )

        # Convert queryset to list
        data["active_sessions_by_group"] = list(active_sessions_by_group)

    elif trend_type == "retention":
        today = now()

        # Get unique users for the last 7 days
        last_7_days = (
            LoginHistoryModel.objects.filter(login_time__gte=today - timedelta(days=7))
            .values("user")
            .distinct()
            .count()
        )  # Count distinct users

        # Get unique users for the last 30 days
        last_30_days = (
            LoginHistoryModel.objects.filter(login_time__gte=today - timedelta(days=30))
            .values("user")
            .distinct()
            .count()
        )  # Count distinct users

        data = {
            "last_7_days": last_7_days,
            "last_30_days": last_30_days,
        }

    else:
        return JsonResponse({"error": "Invalid trend type"}, status=400)

    return JsonResponse(data, safe=False)


def userDemographics(request):
    group_by = request.GET.get("group_by", "home_state")

    valid_fields = ["gender", "home_state", "graduation_year", "major", "status"]
    if group_by not in valid_fields:
        return JsonResponse({"error": "Invalid group_by field"}, status=400)

    demographics = (
        UserProfile.objects.values(group_by)
        .annotate(count=Count("id"))
        .order_by(group_by)
    )

    labels = [demo[group_by] or "Unknown" for demo in demographics]
    counts = [demo["count"] for demo in demographics]

    return JsonResponse({"labels": labels, "counts": counts})


# College Analytics API
def collegeOverview(request):
    data = {}

    # Get colleges grouped by state and count the number of colleges per state
    state_data = (
        College.objects.values("state")
        .annotate(
            college_count=Count("collegeId")
        )  # Replace "id" with your actual field name if different
        .order_by("state")
    )

    data["colleges_by_state"] = list(state_data)

    # Get colleges grouped by city and count the number of colleges per city
    city_data = (
        College.objects.values("city")
        .annotate(
            college_count=Count("collegeId")
        )  # Replace "id" with your actual field name if different
        .order_by("city")
    )

    data["colleges_by_city"] = list(city_data)

    return JsonResponse(data, safe=False)


def collegeMembership(request):
    data = {}

    membership_data = (
        Membership.objects.values("college__name")
        .annotate(member_count=Count("user"))  # Count the distinct users
        .order_by("college__name")
    )

    # Convert to list for JSON serialization
    data["members_by_college"] = list(membership_data)

    return JsonResponse(data, safe=False)


def organizationOverview(request):
    organizations_by_college_privacy = (
        Organization.objects.values("college__name", "privacy")
        .annotate(org_count=Count("orgId"))
        .order_by("college__name", "privacy")
    )

    # Additional grouping by privacy only (if needed for typeSelect)
    organizations_by_privacy = (
        Organization.objects.values("privacy")
        .annotate(org_count=Count("orgId"))
        .order_by("privacy")
    )

    return JsonResponse(
        {
            "organizations_by_college_privacy": list(organizations_by_college_privacy),
            "organizations_by_privacy": list(organizations_by_privacy),
        }
    )


def organizationMembership(request):
    total_memberships = OrganizationMembership.objects.count()

    # Churn Rate (percentage of members who left in the last month, as an example)
    current_month = OrganizationMembership.objects.filter(
        joined_on__month=datetime.now().month
    ).count()
    last_month = OrganizationMembership.objects.filter(
        joined_on__month=(datetime.now().month - 1) % 12
    ).count()
    churn_rate = ((last_month - current_month) / last_month * 100) if last_month else 0

    # Privacy comparison
    privacy_counts = Organization.objects.values("privacy").annotate(
        count=Count("organizationmembership")
    )

    # College comparison
    college_counts = College.objects.values("name").annotate(
        count=Count("organizations__organizationmembership")
    )

    # Membership distribution
    organization_sizes = Organization.objects.annotate(
        member_count=Count("organizationmembership")
    ).values("name", "member_count")

    # Top organizations with the highest number of members
    top_organizations = (
        Organization.objects.annotate(member_count=Count("organizationmembership"))
        .order_by("-member_count")[:5]
        .values("name", "member_count")
    )

    # Most active colleges
    active_colleges = (
        College.objects.annotate(
            total_memberships=Count("organizations__organizationmembership")
        )
        .order_by("-total_memberships")[:5]
        .values("name", "total_memberships")
    )

    # User membership count
    user_membership_distribution = (
        OrganizationMembership.objects.values("user__username")
        .annotate(org_count=Count("organization"))
        .order_by("-org_count")
    )

    # Repeat memberships
    repeat_memberships = sum(
        1 for user in user_membership_distribution if user["org_count"] > 1
    )

    # Membership trends over time
    membership_trends = (
        OrganizationMembership.objects.annotate(month=TruncMonth("joined_on"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    # Convert `month` to a string
    membership_trends = [
        {"month": trend["month"].strftime("%Y-%m"), "count": trend["count"]}
        for trend in membership_trends
    ]

    return JsonResponse(
        {
            "total_memberships": total_memberships,
            "churn_rate": churn_rate,
            "privacy_comparison": list(privacy_counts),
            "college_comparison": list(college_counts),
            "organization_sizes": list(organization_sizes),
            "top_organizations": list(top_organizations),
            "active_colleges": list(active_colleges),
            "user_membership_distribution": list(user_membership_distribution),
            "repeat_memberships": repeat_memberships,
            "membership_trends": membership_trends,
        }
    )



# Host Analytics API
@csrf_exempt
def trackEventClicks(request):
    print("Request Body:", request.body)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event = Event.objects.get(eventId=data["event_id"])
            
            user = request.user if request.user.is_authenticated else None
            guest = None
            if not user:
                guest, _ = GuestUser.objects.get_or_create(guestId=request.session.session_key)
            
            interation = InteractiveEventControl.objects.create(
                event=event,
                user=user,
                guest=guest,
                interaction_type="Clicked",
            )
            print(interation)
            return JsonResponse({"message": "Event click tracked successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def trackEventViews(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event = Event.objects.get(eventId=data["event_id"])
            
            duration = data.get("duration", 0)
            user = request.user if request.user.is_authenticated else None
            guest = None
            if not user:
                guest, _ = GuestUser.objects.get_or_create(guestId=request.session.session_key)
                
            InteractiveEventControl.objects.create(
                event=event,
                user=user,
                guest=guest,
                interaction_type="Viewed",
                duration=duration,
            )
            
            return JsonResponse({"message": "Event view tracked successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)