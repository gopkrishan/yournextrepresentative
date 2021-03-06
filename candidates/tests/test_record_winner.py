from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django_webtest import WebTest

from popolo.models import Person

from ..models import PostExtraElection
from .auth import TestUserMixin
from .settings import SettingsMixin
from .factories import (
    CandidacyExtraFactory, MembershipFactory, PersonExtraFactory,
)
from .dates import processors_after
from .uk_examples import UK2015ExamplesMixin


class TestRecordWinner(TestUserMixin, SettingsMixin, UK2015ExamplesMixin, WebTest):

    def setUp(self):
        super(TestRecordWinner, self).setUp()
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.dulwich_post_extra.base,
            base__on_behalf_of=self.labour_party_extra.base
            )
        MembershipFactory.create(
            person=person_extra.base,
            organization=self.labour_party_extra.base
        )

        winner = PersonExtraFactory.create(
            base__id='4322',
            base__name='Helen Hayes'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=winner.base,
            base__post=self.dulwich_post_extra.base,
            base__on_behalf_of=self.labour_party_extra.base
            )

        MembershipFactory.create(
            person=winner.base,
            organization=self.labour_party_extra.base
        )

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=processors_after)
    def test_record_winner_link_present(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_record_results,
        )
        self.assertIn(
            'This candidate was elected!',
            response.text,
        )
        record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        self.assertIn(
            record_url,
            response.text,
        )

    def test_record_winner_link_not_present(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        self.assertNotIn(
            'This candidate won!',
            response.text
        )

    def test_record_winner_not_privileged(self):
        # Get the constituency page just to set the CSRF token
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        csrftoken = self.app.cookies['csrftoken']
        base_record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            expect_errors=True,
        )
        self.assertEqual(form_get_response.status_code, 403)
        post_response = self.app.post(
            base_record_url,
            {
                'csrfmiddlewaretoken': csrftoken,
                'person_id': '4322',
                'source': 'BBC news',
            },
            expect_errors=True,
        )
        self.assertEqual(post_response.status_code, 403)

    def test_record_winner_privileged(self):
        base_record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=4322)
        self.assertTrue(person.extra.get_elected(self.election))

    def test_cannot_record_multiple_winners(self):
        base_record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=4322)
        self.assertTrue(person.extra.get_elected(self.election))

        form_get_response = self.app.get(
            base_record_url + '?person=2009',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        with self.assertRaises(Exception) as context:
            submission_response = form.submit()
            self.assertEqual('There were already 1 winners' in context.exception)

    def test_record_multiple_winners(self):
        self.election.people_elected_per_post = 2
        self.election.save()
        base_record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=4322)
        self.assertTrue(person.extra.get_elected(self.election))

        form_get_response = self.app.get(
            base_record_url + '?person=2009',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=2009)
        self.assertTrue(person.extra.get_elected(self.election))

    def test_record_multiple_winners_per_post_setting(self):
        post_election = PostExtraElection.objects.get(
            postextra=self.dulwich_post_extra,
            election=self.election
        )
        post_election.winner_count = 2
        post_election.save()
        base_record_url = reverse(
            'record-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=4322)
        self.assertTrue(person.extra.get_elected(self.election))

        form_get_response = self.app.get(
            base_record_url + '?person=2009',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms['record_winner']
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=2009)
        self.assertTrue(person.extra.get_elected(self.election))

class TestRetractWinner(TestUserMixin, SettingsMixin, UK2015ExamplesMixin, WebTest):

    def setUp(self):
        super(TestRetractWinner, self).setUp()
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.dulwich_post_extra.base,
            base__on_behalf_of=self.labour_party_extra.base
            )
        MembershipFactory.create(
            person=person_extra.base,
            organization=self.labour_party_extra.base
        )

        winner = PersonExtraFactory.create(
            base__id='4322',
            base__name='Helen Hayes'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=winner.base,
            base__post=self.dulwich_post_extra.base,
            base__on_behalf_of=self.labour_party_extra.base,
            elected=True
            )

        MembershipFactory.create(
            person=winner.base,
            organization=self.labour_party_extra.base
        )

    def test_retract_winner_link_present(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_record_results,
        )
        self.assertIn(
            'Unset the current winners',
            response.text,
        )
        record_url = reverse(
            'retract-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        self.assertIn(
            record_url,
            response.text,
        )

    def test_retract_winner_link_not_present(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        self.assertNotIn(
            'Unset the current winners',
            response.text
        )

    def test_retract_winner_not_privileged(self):
        # Get the constituency page just to set the CSRF token
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        csrftoken = self.app.cookies['csrftoken']
        base_record_url = reverse(
            'retract-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            expect_errors=True,
        )
        self.assertEqual(form_get_response.status_code, 403)
        post_response = self.app.post(
            base_record_url,
            {
                'csrfmiddlewaretoken': csrftoken,
                'person_id': '4322',
                'source': 'BBC news',
            },
            expect_errors=True,
        )
        self.assertEqual(post_response.status_code, 403)

    def test_retract_winner_privileged(self):
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_record_results,
        )
        csrftoken = self.app.cookies['csrftoken']
        base_record_url = reverse(
            'retract-winner',
            kwargs={
                'election': '2015',
                'post_id': '65808',
            }
        )
        response = self.app.post(
            base_record_url,
            {
                'csrfmiddlewaretoken': csrftoken,
            },
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            'http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood',
        )

        person = Person.objects.get(id=4322)
        self.assertFalse(person.extra.get_elected(self.election))
