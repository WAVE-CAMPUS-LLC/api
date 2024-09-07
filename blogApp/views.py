from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404


from .forms import createBlogForm
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
            
    return render(request, "blogApp/blogItem.html", {"pageName": pageName, "blog":blogItem})