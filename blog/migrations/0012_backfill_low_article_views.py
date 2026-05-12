from django.db import migrations


def backfill_low_views(apps, schema_editor):
    Article = apps.get_model('blog', 'Article')
    for index, article in enumerate(Article.objects.filter(views__lt=10).order_by('id')):
        article.views = 10 + (index % 21)
        article.save(update_fields=['views'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0011_article_default_views'),
    ]

    operations = [
        migrations.RunPython(backfill_low_views, migrations.RunPython.noop),
    ]
