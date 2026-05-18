from django.db import models
from django.utils.translation import gettext_lazy as _


class ContentBlock(models.Model):
    key = models.CharField(max_length=100, unique=True)
    payload = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Content Block')
        verbose_name_plural = _('Content Blocks')

    def __str__(self):
        return self.key
