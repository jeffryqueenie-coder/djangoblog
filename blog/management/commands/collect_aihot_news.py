from django.core.management.base import BaseCommand

from blog.services.collectors import collect_aihot_news


class Command(BaseCommand):
    help = '从 AI HOT 抓取新闻并保存到新闻页'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=30)
        parser.add_argument('--hours', type=int, default=None)

    def handle(self, *args, **options):
        result = collect_aihot_news(limit=options['limit'], hours=options['hours'])
        self.stdout.write(self.style.SUCCESS(
            f'AI HOT news: created={result.created}, skipped={result.skipped}, failed={result.failed}'
        ))
