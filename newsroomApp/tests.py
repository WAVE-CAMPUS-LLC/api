from django.test import TestCase, Client
from django.urls import reverse
from adminDashboardApp.models import Newsroom
from django.contrib.auth.models import User

class NewsArticleTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.news_article = Newsroom.objects.create(
            title='Test News Article',
            body='This is a test news article.',
            newsCategory='The HQ',
            urgencyLevel='THE LATEST',
            created_by=self.user
        )

    def test_news_article_creation(self):
        self.assertEqual(self.news_article.title, 'Test News Article')
        self.assertEqual(self.news_article.body, 'This is a test news article.')

    def test_news_article_update(self):
        self.news_article.title = 'Updated News Article'
        self.news_article.save()
        self.assertEqual(self.news_article.title, 'Updated News Article')

    def test_news_article_deletion(self):
        self.news_article.delete()
        self.assertFalse(Newsroom.objects.filter(title='Test News Article').exists())

    def test_news_article_comments(self):
        response = self.client.post(reverse('newsroom:news', args=[self.news_article.newsId]), {
            'comment': 'This is a test comment.'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.news_article.comments.filter(body='This is a test comment.').exists())

    def test_news_article_likes(self):
        response = self.client.post(reverse('newsroom:news', args=[self.news_article.newsId]), {
            'like': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.news_article.likes.filter(id=self.user.id).exists())

    def test_news_article_search(self):
        response = self.client.get(reverse('newsroom:home'), {'search': 'Test News Article'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test News Article')

    def test_news_article_filtering(self):
        response = self.client.get(reverse('newsroom:home'), {'filter': 'The HQ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test News Article')
