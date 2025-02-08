from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Blog

class BlogPostTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

    def test_blog_post_creation(self):
        response = self.client.post(reverse('blog:createBlog'), {
            'blogType': 'Review',
            'title': 'Test Blog Post',
            'body': 'This is a test blog post.',
            'mood': 'Neutral'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Blog.objects.filter(title='Test Blog Post').exists())

    def test_blog_post_update(self):
        blog = Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.post(reverse('blog:blogView', args=[blog.blogId]), {
            'field': 'title-info',
            'title': 'Updated Blog Post'
        })
        self.assertEqual(response.status_code, 200)
        blog.refresh_from_db()
        self.assertEqual(blog.title, 'Updated Blog Post')

    def test_blog_post_deletion(self):
        blog = Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.post(reverse('blog:blogView', args=[blog.blogId]), {
            'field': 'delete-info'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Blog.objects.filter(title='Test Blog Post').exists())

    def test_blog_post_comments(self):
        blog = Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.post(reverse('blog:blogView', args=[blog.blogId]), {
            'field': 'comment-info',
            'comment': 'This is a test comment.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(blog.comments.filter(body='This is a test comment.').exists())

    def test_blog_post_likes(self):
        blog = Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.post(reverse('blog:blogView', args=[blog.blogId]), {
            'field': 'like-info'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(blog.likes.filter(id=self.user.id).exists())

    def test_blog_post_search(self):
        Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.get(reverse('blog:home'), {'search': 'Test Blog Post'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')

    def test_blog_post_filtering(self):
        Blog.objects.create(
            blogType='Review',
            title='Test Blog Post',
            body='This is a test blog post.',
            mood='Neutral',
            created_by=self.user
        )
        response = self.client.get(reverse('blog:home'), {'filter': 'Review'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')
