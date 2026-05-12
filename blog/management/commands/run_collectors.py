from django.core.management.base import BaseCommand

from blog.services.collectors import run_collectors_loop


class Command(BaseCommand):
    help = '循环运行新闻和技术文章采集任务'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=1800, help='循环间隔秒数，默认 1800')

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS(f'Collectors loop started, interval={interval}s'))
        run_collectors_loop(interval=interval)
