from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-managed "created" and "modified" fields.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
        help_text=_("The date and time this object was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
        help_text=_("The date and time this object was last updated."),
    )

    class Meta:
        abstract = True


class ActiveManager(models.Manager):
    """
    An active manager that returns only active objects.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SoftDeleteModel(models.Model):
    """
    An abstract base class model that provides self-managed "deleted" field.
    """

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active"),
        help_text=_("Whether this object is active."),
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Deleted at"),
        help_text=_("The date and time this object was deleted."),
    )

    objects = models.Manager()
    active_objects = ActiveManager()

    class Meta:
        abstract = True

    def soft_delete(self, *args, **kwargs):
        from django.utils import timezone

        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def restore(self, *args, **kwargs):
        self.is_active = True
        self.deleted_at = None
        self.save()


class AuditModel(models.Model):
    """
    An abstract base class model that provides self-managed "created" and "modified" fields.
    """

    created_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set",
        verbose_name=_("Created by"),
        help_text=_("The user who created this object."),
    )
    updated_by = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set",
        verbose_name=_("Updated by"),
        help_text=_("The user who last updated this object."),
    )

    class Meta:
        abstract = True
