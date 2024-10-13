from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from .forms import SupportTicketForm, FeedbackForm
from .models import SupportTicket
from django.http import JsonResponse
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from django.views.decorators.csrf import csrf_exempt
import json
import os
from difflib import SequenceMatcher

# Hardcoded platform-specific questions
hardcoded_questions = [
    {
        "question": "How can I reset my password?",
        "answer": "You can reset your password by clicking the 'Forgot Password' link on the login page.",
        "keywords": ["reset", "password"],
    },
    {
        "question": "How do I cancel my subscription?",
        "answer": "You can cancel your subscription by going to the subscription settings in your account.",
        "keywords": ["cancel", "subscription"],
    },
    {
        "question": "What is the refund policy?",
        "answer": "Our refund policy allows for a full refund within 30 days of purchase.",
        "keywords": ["refund"],
    },
    {
        "question": "How do I log in?",
        "answer": "Click the 'Login' button on the homepage and enter your email and password.",
        "keywords": ["login", "log in", "sign in"],
    },
    {
        "question": "How can I contact support?",
        "answer": "You can contact support by clicking on the 'Support' tab on our website.",
        "keywords": ["contact", "support", "help"],
    },
    {
        "question": "What is WAVE?",
        "answer": "WAVE is a platform designed to revolutionize campus entertainment by providing seamless event ticketing and management solutions.",
        "keywords": ["WAVE"],
    },
    {
        "question": "How do I create an account?",
        "answer": "To create an account, go to the sign-up page, fill in your details, and submit the form.",
        "keywords": ["create", "account", "sign up", "register"],
    },
    {
        "question": "How do I purchase event tickets?",
        "answer": "Go to the event page, select your tickets, and complete the payment process.",
        "keywords": ["purchase", "tickets", "event", "buy"],
    },
    {
        "question": "Can I attend events on other campuses?",
        "answer": "Yes! WAVE allows students to attend events on any participating campus across the country.",
        "keywords": ["other campuses"],
    },
    {
        "question": "How do QR codes work for event entry?",
        "answer": "After purchasing a ticket, a QR code will be generated. Present this code at the event entrance for validation.",
        "keywords": ["QR code", "event entry", "scan", "ticket"],
    },
    {
        "question": "What is a Crew?",
        "answer": "The Crew System allows you to form groups with friends to attend events together. You can invite friends to your crew by searching for their profiles and simply clicking the 'Invite to Crew' button.",
        "keywords": ["Crew"],
    },
    {
        "question": "How do I create an account on WAVE?",
        "answer": "To create an account, click on the 'Sign Up' button on the homepage and follow the instructions.",
        "keywords": ["create", "account", "sign up"],
    },
    {
        "question": "How can I verify my email address?",
        "answer": "You can verify your email by clicking on the link sent to your email address upon registration.",
        "keywords": ["verify", "email"],
    },
    {
        "question": "What should I do if I forget my password?",
        "answer": "Click on 'Forgot Password' on the login page and follow the instructions to reset your password.",
        "keywords": ["forgot", "password", "reset"],
    },
    {
        "question": "How do I update my profile information on WAVE?",
        "answer": "Go to your profile page and click on the 'Edit Profile' button to update your information.",
        "keywords": ["update", "profile", "edit"],
    },
    {
        "question": "How can I find events near me?",
        "answer": "Use the search feature on the WAVE homepage to filter events based on your location.",
        "keywords": ["find", "events", "near me"],
    },
    {
        "question": "How do I join a crew on WAVE?",
        "answer": "Search for the crew in the 'Crews' section or accept an invitation from a friend.",
        "keywords": ["join", "crew"],
    },
    {
        "question": "How do I leave a crew?",
        "answer": "Go to the crew page, click on 'Leave Crew,' and confirm your decision.",
        "keywords": ["leave", "crew"],
    },
    {
        "question": "What types of events can I create on WAVE?",
        "answer": "You can create events such as parties, study sessions, concerts, sports events, and more.",
        "keywords": ["types", "events", "create"],
    },
    {
        "question": "How can I invite friends to join WAVE?",
        "answer": "Use the 'Invite Friends' option in your account settings to send invites via email or social media.",
        "keywords": ["invite", "friends", "join"],
    },
    {
        "question": "How do I accept a friend request on WAVE?",
        "answer": "Go to the 'Notifications' section, find the friend request, and click 'Accept.'",
        "keywords": ["accept", "friend request"],
    },
    {
        "question": "What is the WAVE Crew feature?",
        "answer": "The Crew feature allows users to create or join groups of friends to attend events together.",
        "keywords": ["wave", "crew", "feature"],
    },
    {
        "question": "Can I customize my event page on WAVE?",
        "answer": "Yes, you can customize your event page by adding descriptions, images, and setting ticket prices.",
        "keywords": ["customize", "event", "page"],
    },
    {
        "question": "How do I block someone on WAVE?",
        "answer": "Go to the user's profile, click on the options menu, and select 'Block User.'",
        "keywords": ["block", "user"],
    },
    {
        "question": "How do I report inappropriate content on WAVE?",
        "answer": "Click on the report button next to the content and select the reason for your report.",
        "keywords": ["report", "inappropriate", "content"],
    },
    {
        "question": "What is the refund policy for event tickets?",
        "answer": "The refund policy varies by event; please check the event details for specific refund information.",
        "keywords": ["refund", "policy", "tickets"],
    },
    {
        "question": "How do I contact WAVE support?",
        "answer": "You can contact support through the 'Help & Support' section or by emailing support@wave.com.",
        "keywords": ["contact", "support", "help"],
    },
    {
        "question": "How can I deactivate my WAVE account?",
        "answer": "Go to 'Account Settings,' click on 'Deactivate Account,' and follow the instructions.",
        "keywords": ["deactivate", "account"],
    },
    {
        "question": "What should I do if I encounter a technical issue on the app?",
        "answer": "Try restarting the app or checking your internet connection. If the issue persists, contact support.",
        "keywords": ["technical", "issue", "troubleshoot"],
    },
    {
        "question": "How do I become a crew leader on WAVE?",
        "answer": "Create a new crew, and as the creator, you will automatically be designated as the leader.",
        "keywords": ["crew", "leader", "create"],
    },
    {
        "question": "What are the benefits of joining a crew?",
        "answer": "Joining a crew allows you to connect with others who share your interests and attend events together.",
        "keywords": ["benefits", "join", "crew"],
    },
    {
        "question": "How can I change my communication preferences on WAVE?",
        "answer": "Go to 'Settings' and update your communication preferences to receive notifications via email or SMS.",
        "keywords": ["communication", "preferences", "settings"],
    },
    {
        "question": "How can I get featured on WAVE's event page?",
        "answer": "Host a popular or unique event and engage with the community to increase your chances of being featured.",
        "keywords": ["featured", "event", "page"],
    },
    {
        "question": "What types of events are most popular on WAVE?",
        "answer": "The most popular events include concerts, parties, workshops, and community gatherings.",
        "keywords": ["popular", "events", "types"],
    },
    {
        "question": "How do I purchase a ticket for an event on WAVE?",
        "answer": "Click on the event, select the ticket type, and proceed to payment to purchase your ticket.",
        "keywords": ["purchase", "ticket", "event"],
    },
    {
        "question": "Can I transfer my event ticket to someone else?",
        "answer": "Currently, ticket transfers are not available, but you can contact support for assistance.",
        "keywords": ["transfer", "ticket"],
    },
    {
        "question": "How do I know if an event has been canceled?",
        "answer": "You'll receive a notification if an event you're attending is canceled or postponed.",
        "keywords": ["event", "canceled", "notification"],
    },
    {
        "question": "What is the WAVE loyalty program?",
        "answer": "The WAVE loyalty program rewards users with points for attending events and participating in activities.",
        "keywords": ["loyalty", "program", "rewards"],
    },
    {
        "question": "How do I earn points on WAVE?",
        "answer": "You can earn points by attending events, inviting friends, and actively engaging on the platform.",
        "keywords": ["earn", "points", "wave"],
    },
    {
        "question": "How do I use my points on WAVE?",
        "answer": "Points can be redeemed for discounts on tickets, exclusive event access, and other perks.",
        "keywords": ["use", "points", "redeem"],
    },
    {
        "question": "How can I become a verified user on WAVE?",
        "answer": "To become verified, update your profile with accurate information and link your social accounts.",
        "keywords": ["verified", "user", "profile"],
    },
    {
        "question": "How do I receive notifications about new events on WAVE?",
        "answer": "Enable notifications in your account settings to stay updated on new and upcoming events.",
        "keywords": ["notifications", "new events", "wave"],
    },
    {
        "question": "How do I edit my event details on WAVE?",
        "answer": "You can edit your event details by navigating to the event page and clicking on 'Edit Event.'",
        "keywords": ["edit", "event", "details"],
    },
    {
        "question": "How do I cancel an event I created on WAVE?",
        "answer": "To cancel an event, go to the event page and select 'Cancel Event' from the options menu.",
        "keywords": ["cancel", "event", "created"],
    },
    {
        "question": "How do I share an event on social media?",
        "answer": "Click on the share icon on the event page to post it directly to your social media accounts.",
        "keywords": ["share", "event", "social media"],
    },
    {
        "question": "What should I do if I didn’t receive my email verification code?",
        "answer": "Check your spam folder and ensure you entered the correct email. If not, request a new code.",
        "keywords": ["email", "verification", "code"],
    },
    {
        "question": "How can I add friends from my contacts on WAVE?",
        "answer": "Sync your phone or email contacts with WAVE to find and add friends who are already using the app.",
        "keywords": ["add", "friends", "contacts"],
    },
    {
        "question": "Can I attend an event without joining a crew?",
        "answer": "Yes, you can attend events on your own without joining a crew, but joining a crew enhances your experience.",
        "keywords": ["attend", "event", "without crew"],
    },
    {
        "question": "How do I find events happening on other campuses?",
        "answer": "Use the location filter on the event search page to find events at other campuses or universities.",
        "keywords": ["find", "events", "other campuses"],
    },
    {
        "question": "What payment methods are accepted for event tickets?",
        "answer": "WAVE accepts credit cards, debit cards, and digital wallets for ticket purchases.",
        "keywords": ["payment", "methods", "tickets"],
    },
    {
        "question": "How do I set my privacy settings on WAVE?",
        "answer": "Go to 'Account Settings,' then 'Privacy Settings,' and customize what information is visible to others.",
        "keywords": ["privacy", "settings", "account"],
    },
    {
        "question": "What are crews on WAVE?",
        "answer": "Crews are groups of users who join together to share experiences and attend events as a team.",
        "keywords": ["crews", "groups", "events"],
    },
    {
        "question": "How do I change my username on WAVE?",
        "answer": "Go to your profile, click on 'Edit Profile,' and update your username.",
        "keywords": ["change", "username", "profile"],
    },
    {
        "question": "Can I delete my WAVE account permanently?",
        "answer": "Yes, you can permanently delete your account by going to 'Account Settings' and selecting 'Delete Account.'",
        "keywords": ["delete", "account", "permanently"],
    },
    {
        "question": "What if I don’t want to receive event recommendations?",
        "answer": "You can disable event recommendations by updating your preferences in the 'Settings' menu.",
        "keywords": ["event", "recommendations", "disable"],
    },
    {
        "question": "How do I know if someone accepted my crew invite?",
        "answer": "You'll receive a notification when someone accepts your invite to join a crew.",
        "keywords": ["crew", "invite", "accepted"],
    },
    {
        "question": "How do I get early access to tickets on WAVE?",
        "answer": "Join exclusive crews or become a loyal user to gain early access to tickets for popular events.",
        "keywords": ["early access", "tickets", "exclusive"],
    },
    {
        "question": "How do I use my discount code on WAVE?",
        "answer": "Apply your discount code at checkout to reduce the total cost of your ticket purchase.",
        "keywords": ["discount code", "checkout", "ticket"],
    },
    {
        "question": "Can I save my favorite events on WAVE?",
        "answer": "Yes, you can save events by clicking the 'Favorite' button on the event page for easy access later.",
        "keywords": ["save", "favorite", "events"],
    },
    {
        "question": "How do I share my crew with friends?",
        "answer": "Use the 'Share Crew' button on the crew page to send invites via social media or direct links.",
        "keywords": ["share", "crew", "friends"],
    },
    {
        "question": "What do I do if my ticket isn't showing up in my account?",
        "answer": "Refresh the page or check your purchase history. If the issue persists, contact support.",
        "keywords": ["ticket", "not showing", "account"],
    },
    {
        "question": "How can I filter events by category on WAVE?",
        "answer": "Use the category filters on the event search page to narrow down events based on your interests.",
        "keywords": ["filter", "events", "category"],
    },
    {
        "question": "How do I join a crew on WAVE?",
        "answer": "You can join a crew by accepting an invite or by requesting to join a public crew from the crew's page.",
        "keywords": ["join", "crew", "invite"],
    },
    {
        "question": "What are the benefits of creating a crew on WAVE?",
        "answer": "Creating a crew lets you connect with like-minded individuals, organize events together, and get crew-based recommendations.",
        "keywords": ["benefits", "create", "crew"],
    },
    {
        "question": "How can I find new events near my location?",
        "answer": "Use the 'Near Me' filter on the events page to discover events happening close to your current location.",
        "keywords": ["find", "events", "near me"],
    },
    {
        "question": "How do I invite friends to join WAVE?",
        "answer": "Go to the 'Invite Friends' section in the app, and send invites via email, SMS, or social media links.",
        "keywords": ["invite", "friends", "join"],
    },
    {
        "question": "Can I set reminders for events I’m interested in?",
        "answer": "Yes, you can set reminders for events by clicking on the 'Set Reminder' button on the event page.",
        "keywords": ["set", "reminders", "events"],
    },
    {
        "question": "How do I contact WAVE support?",
        "answer": "You can contact support by visiting the 'Help & Support' section in the app and submitting your inquiry.",
        "keywords": ["contact", "support", "help"],
    },
    {
        "question": "What do I do if my account was suspended?",
        "answer": "If your account was suspended, please reach out to WAVE support with your account details for assistance.",
        "keywords": ["account", "suspended", "help"],
    },
    {
        "question": "How do I update my notification preferences?",
        "answer": "Go to 'Settings' and select 'Notifications' to customize how and when you receive alerts from WAVE.",
        "keywords": ["update", "notification", "preferences"],
    },
    {
        "question": "How do I upgrade to a premium membership on WAVE?",
        "answer": "To upgrade to premium, go to your account settings and select the 'Upgrade' option to see membership benefits.",
        "keywords": ["upgrade", "premium", "membership"],
    },
    {
        "question": "How can I see which friends are attending the same event?",
        "answer": "On the event page, look for the 'Friends Attending' section to see which of your friends are also going.",
        "keywords": ["friends", "attending", "event"],
    },
    {
        "question": "How do I report inappropriate behavior on WAVE?",
        "answer": "Use the 'Report' button on the user's profile or on event comments to notify WAVE of inappropriate behavior.",
        "keywords": ["report", "inappropriate", "behavior"],
    },
    {
        "question": "What happens if I miss an event I bought a ticket for?",
        "answer": "If you miss an event, please refer to the event's refund policy or contact support for assistance.",
        "keywords": ["miss", "event", "ticket"],
    },
    {
        "question": "How do I know if my event registration was successful?",
        "answer": "You will receive a confirmation email and see your ticket under the 'My Tickets' section in your profile.",
        "keywords": ["event", "registration", "successful"],
    },
    {
        "question": "Can I get a refund for an event ticket?",
        "answer": "Refunds depend on the event's policy. Check the event details page or contact support for more information.",
        "keywords": ["refund", "ticket", "event"],
    },
    {
        "question": "How do I create a private event on WAVE?",
        "answer": "When creating an event, select the 'Private' option to restrict access to invited guests only.",
        "keywords": ["create", "private", "event"],
    },
    {
        "question": "How can I find upcoming music festivals on WAVE?",
        "answer": "Use the event search feature and filter by 'Music Festivals' to see upcoming events in your area.",
        "keywords": ["find", "music festivals", "upcoming"],
    },
    {
        "question": "How do I follow a specific crew or group?",
        "answer": "Go to the crew's page and click 'Follow' to receive updates about their activities and events.",
        "keywords": ["follow", "crew", "group"],
    },
    {
        "question": "Can I message other WAVE users directly?",
        "answer": "Yes, you can message other users by visiting their profile and clicking on the 'Message' button.",
        "keywords": ["message", "users", "directly"],
    },
    {
        "question": "What does it mean to join a featured crew on WAVE?",
        "answer": "Joining a featured crew gives you access to exclusive events and opportunities within that group.",
        "keywords": ["join", "featured crew", "access"],
    },
    {
        "question": "How do I manage my event attendance list?",
        "answer": "You can manage your attendance list by going to the event page and selecting 'Manage Attendees.'",
        "keywords": ["manage", "event", "attendance list"],
    },
    {
        "question": "How do I change my email address on WAVE?",
        "answer": "Go to your account settings, click on 'Edit Email,' enter your new email address, and save the changes.",
        "keywords": ["change", "email", "address"],
    },
    {
        "question": "How do I deactivate my WAVE account?",
        "answer": "To deactivate your account, visit your account settings, scroll down, and select 'Deactivate Account.'",
        "keywords": ["deactivate", "account", "close"],
    },
    {
        "question": "How can I block another user on WAVE?",
        "answer": "You can block a user by visiting their profile and clicking on the 'Block' button to prevent further interaction.",
        "keywords": ["block", "user", "prevent"],
    },
    {
        "question": "What are the different types of events I can create on WAVE?",
        "answer": "You can create various events, including parties, workshops, meetings, concerts, and networking events.",
        "keywords": ["event types", "create", "wave"],
    },
    {
        "question": "Can I view past events I attended on WAVE?",
        "answer": "Yes, go to your profile and select 'Past Events' to see a list of all events you have attended.",
        "keywords": ["view", "past events", "attended"],
    },
    {
        "question": "How do I recover a deleted event on WAVE?",
        "answer": "Once an event is deleted, it cannot be recovered. You may need to recreate the event if needed.",
        "keywords": ["recover", "deleted", "event"],
    },
    {
        "question": "How can I create a recurring event on WAVE?",
        "answer": "When creating an event, select the 'Recurring' option and set the frequency (daily, weekly, monthly).",
        "keywords": ["create", "recurring", "event"],
    },
    {
        "question": "How do I search for events by date on WAVE?",
        "answer": "Use the date filter on the events page to narrow down your search to events happening on specific dates.",
        "keywords": ["search", "events", "date"],
    },
    {
        "question": "What are verified events on WAVE?",
        "answer": "Verified events are official or premium events that have been checked by the WAVE team for authenticity.",
        "keywords": ["verified", "events", "official"],
    },
    {
        "question": "How do I report a technical issue on WAVE?",
        "answer": "You can report technical issues by visiting the 'Help & Support' section and submitting a report.",
        "keywords": ["report", "technical issue", "support"],
    },
    {
        "question": "Can I share my event on social media from WAVE?",
        "answer": "Yes, you can share your event by clicking on the 'Share' button and selecting your preferred social media platform.",
        "keywords": ["share", "event", "social media"],
    },
    {
        "question": "How do I edit the details of an event I created?",
        "answer": "To edit your event, go to the event page, click 'Edit Event,' make changes, and save your updates.",
        "keywords": ["edit", "event", "details"],
    },
    {
        "question": "What are crew recommendations based on?",
        "answer": "Crew recommendations are based on your interests, event history, and mutual friends on WAVE.",
        "keywords": ["crew", "recommendations", "based"],
    },
    {
        "question": "How can I see upcoming events from my favorite genres?",
        "answer": "Filter events by genre in the event search to find upcoming events that match your favorite genres.",
        "keywords": ["upcoming", "events", "genres"],
    },
    {
        "question": "How do I manage my event invitations on WAVE?",
        "answer": "Manage your event invitations by going to the 'My Invitations' section under your profile settings.",
        "keywords": ["manage", "event", "invitations"],
    },
    {
        "question": "How do I delete my crew on WAVE?",
        "answer": "To delete a crew, go to the crew settings and select the 'Delete Crew' option to remove it permanently.",
        "keywords": ["delete", "crew", "remove"],
    },
    {
        "question": "Can I receive notifications for new friend requests on WAVE?",
        "answer": "Yes, you can enable notifications for friend requests in the 'Notification Settings' under your profile.",
        "keywords": ["notifications", "friend requests", "enable"],
    },
    {
        "question": "How do I join a closed crew on WAVE?",
        "answer": "You can request to join a closed crew by visiting their page and clicking on 'Request to Join.'",
        "keywords": ["join", "closed crew", "request"],
    },
    {
        "question": "How can I see all the public events happening on different campuses?",
        "answer": "Use the 'Explore' feature to browse public events on multiple campuses that are open to everyone.",
        "keywords": ["public events", "campuses", "browse"],
    },
    {
        "question": "What should I do if I don't receive a verification email after signing up?",
        "answer": "Check your spam or junk folder, and if it's not there, request a new verification email from the login page.",
        "keywords": ["verification", "email", "sign up"],
    },
]


# List of greetings or casual conversation starters
greetings = [
    "hey",
    "hello",
    "hi",
    "good morning",
    "good evening",
    "How are you?",
    "What's up?",
    "How's it going?",
    "hey chat",
    "Can I ask you a question?",
]


def find_keywords_in_question(user_question, predefined_question):
    """Checks if any keywords from the predefined question exist in the user question."""
    return any(
        keyword.lower() in user_question.lower()
        for keyword in predefined_question["keywords"]
    )


def find_keywords_in_greetings(user_question):
    """Checks if the user question contains greeting keywords."""
    return any(keyword.lower() in user_question.lower() for keyword in greetings)


@ensure_csrf_cookie
def chat_with_gpt(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")
        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)

        # Step 1: Check for greetings and handle them
        if find_keywords_in_greetings(user_message):
            # If it's a greeting, simply pass it to GPT for conversation
            api_key = os.getenv("openAI_api_key")
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": user_message},
                ],
            )
            chat_response = response.choices[0].message.content
            return JsonResponse({"response": chat_response})

        # Step 2: Check for keyword matches in hardcoded questions
        for hardcoded_q in hardcoded_questions:
            if find_keywords_in_question(user_message, hardcoded_q):
                # If a keyword match is found, return the predefined response
                return JsonResponse({"response": hardcoded_q["answer"]})

        # Step 3: If no keyword match is found, use similarity to find the closest question
        predefined_questions_text = [q["question"] for q in hardcoded_questions]
        vectorizer = TfidfVectorizer().fit_transform(
            predefined_questions_text + [user_message]
        )
        vectors = vectorizer.toarray()
        user_vector = vectors[-1].reshape(1, -1)  # User's question vector
        predefined_vectors = vectors[:-1]  # All predefined question vectors

        similarities = cosine_similarity(user_vector, predefined_vectors).flatten()
        max_similarity = np.max(similarities)
        best_match_index = np.argmax(similarities)

        similarity_threshold = 0.7  # You can adjust this threshold

        if max_similarity > similarity_threshold:
            # Return the most similar question's answer
            best_answer = hardcoded_questions[best_match_index]["answer"]
            return JsonResponse({"response": best_answer})

        # Step 4: If no close match is found, provide fallback response
        ticket_link = "http://127.0.0.1:8000/support/ticket/new/"
        fallback_message = f"I don't fully understand your request. You can create a support ticket <a href='{ticket_link}' target='_blank'>here</a>, and one of our team members will respond to you shortly."
        return JsonResponse({"response": fallback_message})

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


# Create your views here.
@ensure_csrf_cookie
def mainSupportView(request):
    return render(request, "supportCenterApp/support.html")


@login_required(login_url="authentication:login")
def supportPortal(request):
    user_tickets = SupportTicket.objects.filter(user=request.user)

    current_tickets = user_tickets.filter(status="Open")
    previous_tickets = user_tickets.filter(status="Closed")

    if user_tickets.exists():
        return render(
            request,
            "supportCenterApp/portal/support_portal_with_tickets.html",
            {
                "current_tickets": current_tickets,
                "previous_tickets": previous_tickets,
            },
        )
    else:
        return render(
            request, "supportCenterApp/portal/support_portal_without_ticket.html"
        )


@login_required(login_url="authentication:login")
def supportTicket(request):
    if request.method == "POST":
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            support_ticket = form.save(commit=False)
            support_ticket.user = request.user
            support_ticket.save()
            return redirect("support:supportPortal")
    else:
        form = SupportTicketForm()
    return render(request, "supportCenterApp/ticket/createTicket.html", {"form": form})


def userFeedback(request):
    if request.method == "POST":
        support_form = FeedbackForm(request.POST)
        if support_form.is_valid():
            support_form.save()
            return redirect("support:home")
    else:
        support_form = FeedbackForm()
    return render(
        request,
        "supportCenterApp/feedback/provideFeedback.html",
        {"support_form": support_form},
    )


# Views to allow users to view and update their tickets.
def viewTicket(request, ticket_id):
    # Try to retrieve the ticket object by using the ticket_id
    try:
        ticket = SupportTicket.objects.get(ticket_id=ticket_id)
    # If ticket object not found, return an exception error.
    except:
        return render(request, "supportCenterApp/doesNotExist.html", status=404)

    return render(
        request,
        "supportCenterApp/portal/support_ticket_details.html",
        {"ticket": ticket},
    )
