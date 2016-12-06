import os
import json

import requests

from collab.settings import AUTH_USER_MODEL
from django.core.urlresolvers import reverse
from django.db import models

from core.notifications.models import Notification
from core.notifications.email import EmailInfo

NOUN = {
            'serve': 'Service',
            'lead': 'Leadership',
            'innovate': 'Innovation',
        }

MATTERMOST_ENDPOINT = os.getenv('MATTERMOST_ENDPOINT')

PRAISE_TEMPLATE = """### Appreciation for {0}
{1} recently offered these words of thanks to {2}:
> {3}

Light up a colleague's day by posting a note of thanks on a wiki profile!
"""


class Praise(models.Model):
    recipient = models.ForeignKey('core.Person', related_name='recepient')
    praise_nominator = models.ForeignKey(AUTH_USER_MODEL)
    cfpb_value = models.CharField(max_length=100)
    reason = models.TextField()
    date_added = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        url = reverse('staff_directory:show_thanks', args=())
        email_info = EmailInfo(
            subject="You were thanked in the staff directory!",
            text_template='staff_directory/email/user_thanked.txt',
            html_template='staff_directory/email/user_thanked.html',
            to_address=self.recipient.user.email,
        )

        # Notify recipient
        url = reverse('staff_directory:person', args=(self.recipient.user.person.stub,))
        title ="%s thanked you for %s" %\
            (self.praise_nominator.person.full_name,
                NOUN[self.cfpb_value])
        Notification.set_notification(self.praise_nominator,
            self.praise_nominator, "thanked", self, self.recipient.user,
                title, url, email_info)

        return super(Praise, self).save(*args, **kwargs)

    def post_thanks_to_chat(self, channel):
        """
        Send a praise posting to Mattermost channel.
        Returns success/error message
        """

        if not MATTERMOST_ENDPOINT:
            return "MATTERMOST_ENDPOINT wasn't found in env variables."

        hu_text = PRAISE_TEMPLATE.format(
            self.recipient.user.person.full_name,
            self.praise_nominator.person.full_name,
            self.recipient.user.person.full_name,
            self.reason
        )
        print "posted text will be {}".format(hu_text)
        username = 'Molliebot'
        error = 'error posting to Mattermost, status={0}, reason={1}'
        data = {}
        data['text'] = hu_text.strip()
        data['username'] = username
        data['channel'] = channel
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(MATTERMOST_ENDPOINT,
                             headers=headers,
                             data=json.dumps(data))
        if not resp.ok:
            return error.format(resp.status_code, resp.reason)
        else:
            return "Praise posted to Mattermost"
