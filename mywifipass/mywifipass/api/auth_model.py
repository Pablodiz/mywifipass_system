# Copyright (c) 2025, Pablo Diz de la Cruz
# All rights reserved.
# Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from uuid import uuid4

class LoginToken(models.Model):
    """
    Model to store login tokens for user authentication, that are retrieved from the QR code.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(unique=True, default=uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at
