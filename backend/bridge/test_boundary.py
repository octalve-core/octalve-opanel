from django.test import Client, TestCase
from .views import valid_binding

BINDING = 'e60d4718-34b4-4e46-b171-04515159a7b1'

class BoundaryRegressionTests(TestCase):
    def test_entitlement_identifiers_are_exact_integers(self):
        for value in (True, 1.2, '1'):
            with self.subTest(value=value):
                self.assertFalse(valid_binding({'subject_id':value,'service_id':13,
                    'binding_ref':BINDING,'capabilities':['overview']}, 1, 13))

    def test_logout_token_available_during_console_outage(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get('/api/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(client.post('/auth/logout/').status_code, 403)
        self.assertEqual(client.post('/auth/logout/', HTTP_X_CSRFTOKEN=response.json()['csrf_token']).status_code, 302)
