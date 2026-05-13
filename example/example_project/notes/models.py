from django.db import models
from django.utils.translation import gettext_lazy as _


class Note(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("title"))
    body = models.TextField(blank=True, verbose_name=_("body"))

    class Meta:
        verbose_name = _("note")
        verbose_name_plural = _("notes")

    def __str__(self):
        return self.title
