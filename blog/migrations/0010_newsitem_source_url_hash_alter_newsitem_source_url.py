import hashlib
from django.db import migrations, models


def fill_source_url_hash(apps, schema_editor):
    NewsItem = apps.get_model('blog', 'NewsItem')
    for item in NewsItem.objects.all():
        item.source_url_hash = hashlib.sha256(item.source_url.encode('utf-8')).hexdigest()
        item.save(update_fields=['source_url_hash'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0009_newsitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='newsitem',
            name='source_url_hash',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='原文链接哈希'),
        ),
        migrations.RunPython(fill_source_url_hash, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='newsitem',
            name='source_url_hash',
            field=models.CharField(blank=True, default='', max_length=64, unique=True, verbose_name='原文链接哈希'),
        ),
        migrations.AlterField(
            model_name='newsitem',
            name='source_url',
            field=models.URLField(max_length=1000, verbose_name='原文链接'),
        ),
    ]
