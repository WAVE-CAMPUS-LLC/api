from django.shortcuts import get_object_or_404, render, redirect
from adminDashboardApp.models import Newsroom


# Create your views here.
def newsroomView(request):
    

    headline_news = (
        Newsroom.objects.filter(urgencyLevel="THE LATEST")
        .order_by("created_at")
        .first()
    )
    regular_news = Newsroom.objects.filter(urgencyLevel="REGULAR").order_by(
        "created_at"
    )
    pageName = "Newsroom"
    return render(
        request,
        "newsroomApp/newsroom.html",
        {
            "pageName": pageName,
            "headlineNews": headline_news,
            "regularNews": regular_news,
        },
    )


def newsView(request, newsId):
    newsItem = get_object_or_404(Newsroom, newsId=newsId)
    return render(request, "newsroomApp/newsroom/news.html", {'newsItem':newsItem})
