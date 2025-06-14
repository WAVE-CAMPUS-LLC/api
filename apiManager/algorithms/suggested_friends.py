from django.db.models import (
    Q,
    Count,
    F,
    ExpressionWrapper,
    FloatField,
    Case,
    When,
    Value,
)
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from accountManagementApp.models import UserProfile
from authenticationApp.models import CustomUser
from eventTicketsApp.models import Ticket
from socialApp.models import CrewMember


def get_suggested_friends(user: CustomUser, max_suggestions: int = 10):
    """
    Enhanced algorithm for suggesting friends based on multiple factors:
    1. Mutual friends (weighted by number of mutual connections)
    2. Shared events (weighted by recency)
    3. Shared interests (based on groups and crews)
    4. Same college
    5. Cached results for performance
    """
    cache_key = f"suggested_friends_{user.id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    user_profile = user.user_profile
    user_friends = user_profile.friends.all()
    user_events = user_profile.purchased_events.all()
    user_college = user_profile.college

    # Get friends of friends with mutual friend count
    friends_of_friends = (
        UserProfile.objects.filter(friends__in=user_friends)
        .exclude(Q(user_id=user.id) | Q(friends__in=user_friends))
        .annotate(
            mutual_count=Count("friends"),
            # Weight by number of mutual friends (1-5 scale)
            mutual_weight=ExpressionWrapper(
                F("mutual_count") / 5.0, output_field=FloatField()
            ),
        )
        .distinct()
    )

    # Get users from same events, weighted by recency
    recent_date = timezone.now() - timedelta(days=30)  # Last 30 days
    ticket_users = (
        CustomUser.objects.filter(ticket__event__in=user_events)
        .exclude(Q(id=user.id) | Q(user_profile__in=user_friends))
        .annotate(
            # Weight by event recency (1-5 scale)
            event_weight=ExpressionWrapper(
                Case(
                    When(ticket__event__date__gte=recent_date, then=5.0),
                    default=1.0,
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            )
        )
        .distinct()
    )

    # Get users with shared interests (groups and crews)
    user_groups = user_profile.group.all()
    user_crews = CrewMember.objects.filter(user_id=user.id).values_list(
        "crew_id", flat=True
    )

    shared_interests_users = (
        UserProfile.objects.filter(
            Q(group__in=user_groups) | Q(user__crew_memberships__crew_id__in=user_crews)
        )
        .exclude(Q(user_id=user.id) | Q(friends__in=user_friends))
        .annotate(
            # Weight by number of shared interests (1-5 scale)
            interest_weight=ExpressionWrapper(
                Count("group") + Count("user__crew_memberships__crew_id") / 5.0,
                output_field=FloatField(),
            )
        )
        .distinct()
    )

    # Get users from same college
    college_users = (
        UserProfile.objects.filter(college=user_college)
        .exclude(Q(user_id=user.id) | Q(friends__in=user_friends))
        .annotate(
            # College weight is fixed at 3.0
            college_weight=Value(3.0, output_field=FloatField())
        )
        .distinct()
    )

    # Combine all suggestions with their weights
    suggested_users = {}

    # Add friends of friends with mutual friend weight
    for profile in friends_of_friends:
        suggested_users[profile.user] = {
            "weight": profile.mutual_weight,
            "reason": f"{profile.mutual_count} mutual friends",
        }

    # Add event-based suggestions with recency weight
    for user in ticket_users:
        if user in suggested_users:
            suggested_users[user]["weight"] += user.event_weight
            suggested_users[user]["reason"] += f", attended same events"
        else:
            suggested_users[user] = {
                "weight": user.event_weight,
                "reason": "attended same events",
            }

    # Add shared interests suggestions
    for profile in shared_interests_users:
        if profile.user in suggested_users:
            suggested_users[profile.user]["weight"] += profile.interest_weight
            suggested_users[profile.user]["reason"] += f", shared interests"
        else:
            suggested_users[profile.user] = {
                "weight": profile.interest_weight,
                "reason": "shared interests",
            }

    # Add college-based suggestions
    for profile in college_users:
        if profile.user in suggested_users:
            suggested_users[profile.user]["weight"] += profile.college_weight
            suggested_users[profile.user]["reason"] += f", same college"
        else:
            suggested_users[profile.user] = {
                "weight": profile.college_weight,
                "reason": "same college",
            }

    # Sort by total weight and get top suggestions
    sorted_suggestions = sorted(
        suggested_users.items(), key=lambda x: x[1]["weight"], reverse=True
    )[:max_suggestions]

    # Get the final list of suggested users
    suggested_profiles = [user for user, _ in sorted_suggestions]

    # Cache the results for 1 hour
    cache.set(cache_key, suggested_profiles, 3600)

    return suggested_profiles
