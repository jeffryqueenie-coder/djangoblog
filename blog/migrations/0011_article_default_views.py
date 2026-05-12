from django.db import migrations, models

import blog.models


def backfill_zero_views(apps, schema_editor):
    Article = apps.get_model('blog', 'Article')
    for index, article in enumerate(Article.objects.filter(views=0).order_by('id')):
        article.views = 10 + (index % 21)
        article.save(update_fields=['views'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_newsitem_source_url_hash_alter_newsitem_source_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='views',
            field=models.PositiveIntegerField(
                default=blog.models.default_article_views,
                verbose_name='views',
            ),
        ),
        migrations.RunPython(backfill_zero_views, migrations.RunPython.noop),
    ]
