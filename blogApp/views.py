from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.http import HttpResponseBadRequest
from datetime import datetime

from .forms import (
    createBlogForm,
    UpdateBlogTypeForm,
    UpdateBlogTitleForm,
    UpdateBlogBodyForm,
    UpdateImageOneForm,
    UpdateImageTwoForm,
    UpdateImageThreeForm,
    UpdateBlogMoodForm
)
from .models import Blog

# Create your views here.
def blogHomeView(request):
    pageName = "Blog"
    blogItems = Blog.objects.all()
    
    return render(request, "blogApp/blogHome.html", {"pageName": pageName, "blogItems":blogItems})

@login_required
def blogCreateView(request):
    pageName = "createBlog"
    blogForm = createBlogForm(request.POST, request.FILES)
    
    if request.method == "POST":
        if blogForm.is_valid():
            blog_instance = blogForm.save(commit=False)
            blog_instance.created_by = request.user
            blog_instance.save()
            return redirect("blog:home")
            
    return render(request, "blogApp/createBlog.html", {"pageName": pageName, "createBlogForm":blogForm})

def blogView(request, blogId):
    pageName = "blogView"
    blogItem = get_object_or_404(Blog, blogId=blogId)
    time = datetime.now().timestamp()
    
    typeFieldForm = UpdateBlogTypeForm(instance=blogItem)
    titleFieldForm = UpdateBlogTitleForm(instance=blogItem)
    bodyFieldForm = UpdateBlogBodyForm(instance=blogItem)
    imageOneForm = UpdateImageOneForm(instance=blogItem)
    imageTwoForm = UpdateImageTwoForm(instance=blogItem)
    imageThreeForm = UpdateImageThreeForm(instance=blogItem)
    
    if request.method == "POST":
        field = request.POST.get("field")

        if field == "type-info":
            typeFieldForm = UpdateBlogTypeForm(request.POST, instance=blogItem)
            if typeFieldForm.is_valid():
                typeFieldForm.save()
                
        elif field == "title-info":
            titleFieldForm = UpdateBlogTitleForm(request.POST, instance=blogItem)
            if titleFieldForm.is_valid():
                titleFieldForm.save()
        
        
        elif field == "body-info":
            bodyFieldForm = UpdateBlogBodyForm(request.POST, instance=blogItem)
            if bodyFieldForm.is_valid():
                bodyFieldForm.save()

        elif field == "imageOne-info":
            imageOneForm = UpdateImageOneForm(request.POST, request.FILES, instance=blogItem)
            if imageOneForm.is_valid():
                imageOneForm.save()

        elif field == "imageTwo-info":
            imageTwoForm = UpdateImageTwoForm(request.POST, request.FILES, instance=blogItem)
            if imageTwoForm.is_valid():
                imageTwoForm.save()

        elif field == "imageThree-info":
            imageThreeForm = UpdateImageThreeForm(request.POST, request.FILES, instance=blogItem)
            if imageThreeForm.is_valid():
                imageThreeForm.save()
                
        # elif field == "mood-info":
        #     moodFieldForm = UpdateBlogMoodForm(request.POST, instance=blogItem)
        #     if moodFieldForm.is_valid():
        #         moodFieldForm.save()

        else:
            return HttpResponseBadRequest("Invalid form type")
        
    else:
        typeFieldForm = UpdateBlogTypeForm()
        titleFieldForm = UpdateBlogTitleForm()
        bodyFieldForm = UpdateBlogBodyForm()
        imageOneForm = UpdateImageOneForm()
        imageTwoForm = UpdateImageTwoForm()
        imageThreeForm = UpdateImageThreeForm()
            
    return render(
        request, 
        "blogApp/blogItem.html", 
        {
            "pageName": pageName, 
            "blog":blogItem,
            "typeFieldForm":typeFieldForm,
            "titleFieldForm":titleFieldForm,
            "bodyFieldForm":bodyFieldForm,
            "imageOneForm":imageOneForm,
            "imageTwoForm":imageTwoForm,
            "imageThreeForm":imageThreeForm,
            "time": time
        })