from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from .forms import SupportTicketForm, FeedbackForm
from .models import SupportTicket, SupportTicketMessage
from authenticationApp.models import CustomUser
from django.http import JsonResponse
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import json
import os
from difflib import SequenceMatcher

from wave_v1.decorators import check_suspension, member, verified, onboarded


# Hardcoded platform-specific questions
# When adding a question take special care to add unique keywords that are not present in other questions.
# Also for keywords that are likely to appear in other questions but are not necessarily the keywords for the question,
# add those questions to the end of the list because our algorithm does a sequential search. This is of course very crude but
# it is a simple way to ensure that the most relevant question is returned. Our algorithm will be improved in the future when we have more resources to purchase more tokens from OpenAI.

hardcoded_questions = [
    {
        "question": "How can I reset my password?",
        "answer": "You can reset your password by clicking the 'Forgot Password' link on the login page.",
        "keywords": ["reset", "password"],
    },
    {
        "question": "Is there a mobile app version of WAVE?",
        "answer": "We don't yet have a mobile app, but we are working on it! Stay tuned for updates.",
        "keywords": ["mobile", "app"],
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
        "question": "How do I create an account?",
        "answer": "To create an account, go to the sign-up page, fill in your details, and submit the form.",
        "keywords": ["account", "sign up", "register"],
    },
    {
        "question": "How do I purchase event tickets?",
        "answer": "Go to the event page, select your tickets, and complete the payment process.",
        "keywords": ["purchase", "tickets", "event", "buy"],
    },
    {
        "question": "Can I attend events on other campuses?",
        "answer": "Yes! WAVE allows students to attend events on any participating campus across the country.",
        "keywords": [
            "other campuses",
            "other colleges",
        ],
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
        "question": "What is WAVE?",
        "answer": "WAVE is a platform designed to revolutionize campus entertainment by providing seamless event ticketing and management solutions.",
        "keywords": ["WAVE"],
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
    "Thanks",
    "Thank you",
    "Thanks for the help",
    "Good",
    "Great",
    "I need help",
    "Can you help me?",
    "I have a question",
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
        print(max_similarity, best_match_index)
        similarity_threshold = 0.7  # You can adjust this threshold

        if max_similarity > similarity_threshold:
            # Return the most similar question's answer
            best_answer = hardcoded_questions[best_match_index]["answer"]
            return JsonResponse({"response": best_answer})

        # Step 4: If no close match is found, provide fallback response
        
        # In local development, use the website domain from the .env file
        # In production, use the actual website domain
        load_dotenv()
        base_url = os.getenv("WEBSITE_DOMAIN")

        ticket_link = f"{base_url}/support/ticket/new/"
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
    user = CustomUser.objects.get(email=request.user.email)

    if user_tickets.exists():
        return render(
            request,
            "supportCenterApp/portal/support_portal_with_tickets.html",
            {
                "current_tickets": current_tickets,
                "previous_tickets": previous_tickets,
                "current_user": user,
            },
        )
    else:
        return render(
            request, "supportCenterApp/portal/support_portal_without_ticket.html", {"current_user": user,}
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


@login_required(login_url="authentication:login")
def send_ticket_reply(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    if request.method == "POST":
        message = request.POST.get("message")
        if message:
            SupportTicketMessage.objects.create(
                ticket=ticket, sender=request.user, message=message
            )
    return redirect("support:viewTicket", ticket_id=ticket_id)


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


def ticket_messages(request, ticket_id):
    ticket = SupportTicket.objects.get(ticket_id=ticket_id)
    messages = ticket.messages.all()
    return render(request, "partials/messages.html", {"messages": messages})
