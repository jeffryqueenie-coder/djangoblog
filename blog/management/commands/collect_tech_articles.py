from django.core.management.base import BaseCommand

from blog.services.collectors import collect_tech_articles, parse_feed_list


class Command(BaseCommand):
    help = '从技术 RSS 源抓取文章，经 LLM 重写后发布为博客文章'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=5)
        parser.add_argument('--feed', action='append', dest='feeds')

    def handle(self, *args, **options):
        feeds = options.get('feeds') or parse_feed_list()
        result = collect_tech_articles(limit=options['limit'], feeds=feeds)
        self.stdout.write(self.style.SUCCESS(
            f'Tech articles: created={result.created}, skipped={result.skipped}, failed={result.failed}'
        ))
