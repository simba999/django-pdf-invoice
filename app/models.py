# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)

    def __unicode__(self):
        return self.user.email

    @property
    def address(self):
        return self.addresses.latest()