from django.db import migrations
from django.utils import timezone


TECH_CATEGORY_NAMES = [
    '前端开发',
    '后端开发',
    '云原生',
    '数据库',
    'AI 工程',
    '架构设计',
    '工程效能',
    '安全与可观测',
    '云平台',
    '全栈实践',
]


def merge_collected_article_categories(apps, schema_editor):
    Article = apps.get_model('blog', 'Article')
    Category = apps.get_model('blog', 'Category')

    article_category, _ = Category.objects.get_or_create(name='文章')
    old_categories = list(Category.objects.filter(name__in=TECH_CATEGORY_NAMES))
    if not old_categories:
        return

    old_category_ids = [category.id for category in old_categories if category.name != '文章']
    if old_category_ids:
        Article.objects.filter(category_id__in=old_category_ids, type='a').update(category=article_category)

    Article.objects.filter(type='a', pub_time__gt=timezone.now()).update(pub_time=timezone.now())

    for category in old_categories:
        if category.name == '文章':
            continue
        if not Article.objects.filter(category=category).exists():
            category.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0012_backfill_low_article_views'),
    ]

    operations = [
        migrations.RunPython(merge_collected_article_categories, migrations.RunPython.noop),
    ]
