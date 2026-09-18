"""Remove uploaded files from disk when they are replaced, cleared or their row is deleted."""
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Dish, Restaurant

FILE_FIELDS = {Restaurant: ["logo", "hero_image"], Dish: ["image"]}


def delete_file(file):
    if file and file.name:
        file.storage.delete(file.name)


@receiver(pre_save, sender=Restaurant)
@receiver(pre_save, sender=Dish)
def delete_replaced_files(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = sender.objects.filter(pk=instance.pk).first()
    if old is None:
        return
    for field in FILE_FIELDS[sender]:
        old_file, new_file = getattr(old, field), getattr(instance, field)
        if old_file and old_file.name != new_file.name:
            delete_file(old_file)


@receiver(post_delete, sender=Restaurant)
@receiver(post_delete, sender=Dish)
def delete_files_of_deleted_row(sender, instance, **kwargs):
    for field in FILE_FIELDS[sender]:
        delete_file(getattr(instance, field))
