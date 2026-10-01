from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import IssuerProfile, Client, Condition, Document


class BillingAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='billing-test', password='x')
        self.client = APIClient(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)

    def create_doc(self, **data):
        data.setdefault('kind', 'quote')
        return self.client.post('/api/billing/documents/', data, format='json')


class AuthTests(BillingAPITestCase):
    def test_auth_required(self):
        anon = APIClient(HTTP_HOST='localhost')
        for url in ['/api/billing/issuer/', '/api/billing/clients/', '/api/billing/documents/',
                    '/api/billing/documents/next-number/']:
            self.assertEqual(anon.get(url).status_code, status.HTTP_401_UNAUTHORIZED, url)
        self.assertEqual(
            anon.post('/api/billing/documents/', {'kind': 'quote'}, format='json').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class IssuerTests(BillingAPITestCase):
    def test_get_creates_and_put_updates(self):
        self.assertFalse(IssuerProfile.objects.exists())
        res = self.client.get('/api/billing/issuer/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['legal_name'], '')
        self.assertEqual(IssuerProfile.objects.count(), 1)

        payload = {
            'legal_name': 'Andrea Francín', 'tax_id': '12345678Z', 'address': 'Carrer X · 43840 Salou',
            'phone': '600000000', 'website': 'example.com', 'email': 'a@example.com',
            'city': 'Salou', 'iban': 'ES00 0000 0000 0000 0000 0000', 'quote_conditions': 'Condicions...',
        }
        res = self.client.put('/api/billing/issuer/', payload, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['city'], 'Salou')

        res = self.client.patch('/api/billing/issuer/', {'phone': '611111111'}, format='json')
        self.assertEqual(res.data['phone'], '611111111')
        self.assertEqual(res.data['city'], 'Salou')
        self.assertEqual(IssuerProfile.objects.count(), 1)


class ClientTests(BillingAPITestCase):
    def test_crud_and_search(self):
        res = self.client.post('/api/billing/clients/', {'name': 'Ajuntament de Reus', 'tax_id': 'P4312300F'}, format='json')
        self.assertEqual(res.status_code, 201)
        cid = res.data['id']
        self.client.post('/api/billing/clients/', {'name': 'Editorial Bruixa'}, format='json')

        self.assertEqual(len(self.client.get('/api/billing/clients/').data), 2)
        found = self.client.get('/api/billing/clients/?search=reus').data
        self.assertEqual([c['id'] for c in found], [cid])

        res = self.client.patch(f'/api/billing/clients/{cid}/', {'email': 'x@reus.cat'}, format='json')
        self.assertEqual(res.data['email'], 'x@reus.cat')
        self.assertEqual(self.client.get(f'/api/billing/clients/{cid}/').data['name'], 'Ajuntament de Reus')

        self.assertEqual(self.client.delete(f'/api/billing/clients/{cid}/').status_code, 204)
        self.assertEqual(self.client.get(f'/api/billing/clients/{cid}/').status_code, 404)

        self.assertEqual(self.client.post('/api/billing/clients/', {}, format='json').status_code, 400)


class DocumentTests(BillingAPITestCase):
    def test_auto_sequence_per_kind_and_year(self):
        seqs = [self.create_doc(date='2026-03-01').data['sequence'] for _ in range(3)]
        self.assertEqual(seqs, [1, 2, 3])
        self.assertEqual(self.create_doc(kind='invoice', date='2026-03-01').data['sequence'], 1)
        res = self.create_doc(date='2025-12-31')
        self.assertEqual((res.data['year'], res.data['sequence']), (2025, 1))
        self.assertEqual(self.create_doc(year=2026, date='2025-12-31').data['sequence'], 4)

    def test_defaults(self):
        res = self.create_doc()
        self.assertEqual(res.status_code, 201)
        today = timezone.localdate()
        self.assertEqual(res.data['date'], today.isoformat())
        self.assertEqual(res.data['year'], today.year)
        self.assertEqual(res.data['status'], 'draft')
        self.assertEqual(res.data['layout'], 'concept')
        self.assertEqual(res.data['iva_rate'], '21.00')
        self.assertEqual(res.data['irpf_rate'], '15.00')

    def test_totals_style_base_only(self):
        res = self.create_doc(totals_style='base')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['totals_style'], 'base')
        self.assertEqual(self.create_doc(totals_style='nope').status_code, 400)

    def test_sequence_collision(self):
        self.assertEqual(self.create_doc(year=2026, sequence=16).status_code, 201)
        res = self.create_doc(year=2026, sequence=16)
        self.assertEqual(res.status_code, 400)
        self.assertIn('sequence', res.data)
        self.assertIn('26/16', str(res.data['sequence']))
        # same number on another kind is fine
        self.assertEqual(self.create_doc(kind='invoice', year=2026, sequence=16).status_code, 201)
        # update into a taken number
        other = self.create_doc(year=2026, sequence=17).data
        res = self.client.patch(f"/api/billing/documents/{other['id']}/", {'sequence': 16}, format='json')
        self.assertEqual(res.status_code, 400)
        # next auto sequence continues after max
        self.assertEqual(self.create_doc(year=2026).data['sequence'], 18)

    def test_number_format(self):
        res = self.create_doc(year=2026, sequence=16, date='2026-05-01')
        self.assertEqual(res.data['number'], '26/16')
        res = self.create_doc(year=2026, sequence=3, date='2026-05-01')
        self.assertEqual(res.data['number'], '26/03')
        self.assertEqual(Document(year=2100, sequence=120).number, '00/120')

    def test_snapshot_from_client(self):
        c = Client.objects.create(name='Ajuntament de Reus', tax_id='P4312300F', address='Plaça Mercadal, 1\n43201 Reus')
        res = self.create_doc(client=c.id)
        self.assertEqual(res.data['client_snapshot'], {'name': c.name, 'tax_id': c.tax_id, 'address': c.address})
        self.assertEqual(res.data['client_name'], 'Ajuntament de Reus')
        # explicit snapshot is respected
        res = self.create_doc(client=c.id, client_snapshot={'name': 'Custom'})
        self.assertEqual(res.data['client_snapshot'], {'name': 'Custom'})
        # editing the client later doesn't change the document
        c.name = 'Renamed'
        c.save()
        doc = self.client.get(f"/api/billing/documents/{res.data['id']}/").data
        self.assertEqual(doc['client_name'], 'Custom')

    def test_filters(self):
        c = Client.objects.create(name='Reus')
        self.create_doc(date='2026-01-10', client=c.id)
        self.create_doc(date='2025-01-10', client_snapshot={'name': 'Bruixa'})
        self.create_doc(kind='invoice', date='2026-02-10', client_snapshot={'name': 'Bruixa'})

        def ids(q):
            return len(self.client.get('/api/billing/documents/' + q).data)

        self.assertEqual(ids(''), 3)
        self.assertEqual(ids('?kind=quote'), 2)
        self.assertEqual(ids('?kind=invoice'), 1)
        self.assertEqual(ids('?year=2026'), 2)
        self.assertEqual(ids('?kind=quote&year=2025'), 1)
        self.assertEqual(ids(f'?client={c.id}'), 1)
        self.assertEqual(ids('?search=bruix'), 2)
        listed = self.client.get('/api/billing/documents/').data
        self.assertEqual([d['year'] for d in listed], [2026, 2026, 2025])

    def test_next_number(self):
        res = self.client.get('/api/billing/documents/next-number/?kind=quote&year=2026')
        self.assertEqual(res.data, {'kind': 'quote', 'year': 2026, 'sequence': 1, 'number': '26/01'})
        self.create_doc(year=2026, sequence=15)
        res = self.client.get('/api/billing/documents/next-number/?kind=quote&year=2026')
        self.assertEqual(res.data['number'], '26/16')
        res = self.client.get('/api/billing/documents/next-number/?kind=invoice')
        self.assertEqual(res.data['year'], timezone.localdate().year)
        self.assertEqual(res.data['sequence'], 1)
        self.assertEqual(self.client.get('/api/billing/documents/next-number/?kind=foo').status_code, 400)
        self.assertEqual(self.client.get('/api/billing/documents/next-number/?year=abc').status_code, 400)

    def test_duplicate(self):
        year = timezone.localdate().year
        c = Client.objects.create(name='Reus')
        original = self.create_doc(
            date=f'{year - 1}-06-01', client=c.id, layout='numbered', totals_style='summary',
            content={'intro': 'Hola', 'lines': [{'text': 'A', 'amount': '100.00'}]},
            status='sent', base_amount='100.00', total_amount='106.00', conditions_text='Cond',
        ).data
        self.create_doc(date=f'{year}-01-01')  # sequence 1 in current year
        res = self.client.post(f"/api/billing/documents/{original['id']}/duplicate/")
        self.assertEqual(res.status_code, 201)
        d = res.data
        self.assertNotEqual(d['id'], original['id'])
        self.assertEqual((d['kind'], d['year'], d['sequence']), ('quote', year, 2))
        self.assertEqual(d['date'], timezone.localdate().isoformat())
        self.assertEqual(d['status'], 'draft')
        for f in ['client', 'client_snapshot', 'layout', 'totals_style', 'content', 'base_amount',
                  'total_amount', 'conditions_text', 'iva_rate', 'irpf_rate']:
            self.assertEqual(d[f], original[f], f)

    def test_to_invoice(self):
        IssuerProfile.objects.create(pk=1, iban='ES12 3456 7890 1234 5678 9012')
        quote = self.create_doc(
            year=2026, sequence=16, date='2026-04-01', client_snapshot={'name': 'Reus'},
            content={'intro': 'x'}, base_amount='1000.00', iva_amount='210.00',
            irpf_amount='150.00', total_amount='1060.00', layout='numbered', totals_style='summary',
        ).data
        res = self.client.post(f"/api/billing/documents/{quote['id']}/to-invoice/")
        self.assertEqual(res.status_code, 201)
        inv = res.data
        self.assertEqual(inv['kind'], 'invoice')
        self.assertEqual((inv['year'], inv['sequence']), (timezone.localdate().year, 1))
        self.assertEqual(inv['status'], 'draft')
        self.assertEqual(inv['layout'], 'invoice')
        self.assertEqual(inv['totals_style'], 'table')
        self.assertEqual(inv['source_quote'], quote['id'])
        self.assertEqual(inv['source_quote_number'], '26/16')
        self.assertEqual(inv['payment_text'], 'ES12 3456 7890 1234 5678 9012')
        for f in ['client_snapshot', 'content', 'base_amount', 'iva_amount', 'irpf_amount', 'total_amount']:
            self.assertEqual(inv[f], quote[f], f)
        self.assertEqual(Document.objects.get(pk=quote['id']).invoices.count(), 1)

        res = self.client.post(f"/api/billing/documents/{inv['id']}/to-invoice/")
        self.assertEqual(res.status_code, 400)

    def test_delete_client_keeps_documents(self):
        c = Client.objects.create(name='Reus', tax_id='T')
        doc = self.create_doc(client=c.id).data
        self.client.delete(f'/api/billing/clients/{c.id}/')
        res = self.client.get(f"/api/billing/documents/{doc['id']}/")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data['client'])
        self.assertEqual(res.data['client_snapshot']['name'], 'Reus')
        self.assertEqual(res.data['client_name'], 'Reus')

    def test_delete_document(self):
        doc = self.create_doc().data
        self.assertEqual(self.client.delete(f"/api/billing/documents/{doc['id']}/").status_code, 204)
        self.assertFalse(Document.objects.exists())


class ConditionTests(BillingAPITestCase):
    def test_crud(self):
        url = '/api/billing/conditions/'
        r = self.client.post(url, {'title': 'Standard', 'text': 'Two revisions included.'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        cid = r.data['id']
        self.client.post(url, {'title': 'Agency', 'text': 'No print costs.'}, format='json')
        r = self.client.get(url)
        self.assertEqual([c['title'] for c in r.data], ['Agency', 'Standard'])
        r = self.client.patch(f'{url}{cid}/', {'text': 'Three revisions included.'}, format='json')
        self.assertEqual(r.data['text'], 'Three revisions included.')
        self.assertEqual(self.client.delete(f'{url}{cid}/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Condition.objects.count(), 1)

    def test_title_required(self):
        r = self.client.post('/api/billing/conditions/', {'text': 'x'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auth_required(self):
        anon = APIClient(HTTP_HOST='localhost')
        self.assertEqual(anon.get('/api/billing/conditions/').status_code, status.HTTP_401_UNAUTHORIZED)
