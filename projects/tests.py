from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Category, Project


class CategoryTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('tester', password='x')
        self.anon = APIClient(HTTP_HOST='localhost')
        self.api = APIClient(HTTP_HOST='localhost')
        self.api.force_authenticate(user=self.user)

    def test_seeded_and_public(self):
        r = self.anon.get('/api/categories/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual([c['slug'] for c in r.data], ['illustration', 'branding', 'campaigns', 'editorial'])

    def test_writes_need_auth(self):
        r = self.anon.post('/api/categories/', {'name_i18n': {'es': 'Murales'}, 'color': '#123456'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_slug_order_and_validation(self):
        r = self.api.post('/api/categories/', {'name_i18n': {'es': 'Murales', 'en': 'Murals'}, 'color': '#ABCDEF'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['slug'], 'murals')
        self.assertEqual(r.data['color'], '#abcdef')
        self.assertEqual(r.data['order'], 4)
        r2 = self.api.post('/api/categories/', {'name_i18n': {'en': 'Murals'}, 'color': '#000000'}, format='json')
        self.assertEqual(r2.data['slug'], 'murals-2')
        bad = self.api.post('/api/categories/', {'name_i18n': {'es': ''}, 'color': 'red'}, format='json')
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_keeps_slug(self):
        cat = Category.objects.get(slug='branding')
        r = self.api.patch(f'/api/categories/{cat.id}/', {'slug': 'other', 'name_i18n': {'es': 'Marca'}}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['slug'], 'branding')
        self.assertEqual(r.data['name_i18n'], {'es': 'Marca'})

    def test_delete_removes_from_projects(self):
        p = Project.objects.create(title='P', categories=['branding', 'campaigns'])
        cat = Category.objects.get(slug='branding')
        self.assertEqual(self.api.delete(f'/api/categories/{cat.id}/').status_code, status.HTTP_204_NO_CONTENT)
        p.refresh_from_db()
        self.assertEqual(p.categories, ['campaigns'])

    def test_project_rejects_unknown_category(self):
        p = Project.objects.create(title='P')
        r = self.api.patch(f'/api/projects/{p.id}/', {'categories': ['nope']}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.api.patch(f'/api/projects/{p.id}/', {'categories': ['campaigns', 'campaigns']}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['categories'], ['campaigns'])

    def test_reorder(self):
        ids = list(Category.objects.values_list('id', flat=True))[::-1]
        r = self.api.post('/api/categories/reorder/', {'order': ids}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(list(Category.objects.values_list('id', flat=True)), ids)
