import os
import re
import time
import hashlib
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from blog.models import Article, Category, NewsItem, Tag
from djangoblog.utils import cache


logger = logging.getLogger(__name__)
AIHOT_URL = 'https://aihot.virxact.com/'
DEFAULT_TECH_FEEDS = [
    'https://www.djangoproject.com/rss/weblog/',
    'https://realpython.com/atom.xml',
    'https://blog.python.org/feeds/posts/default',
    'https://kubernetes.io/feed.xml',
    'https://www.docker.com/blog/feed/',
    'https://blog.cloudflare.com/rss/',
    'https://github.blog/engineering/feed/',
    'https://netflixtechblog.com/feed/',
    'https://engineering.fb.com/feed/',
    'https://engineering.atspotify.com/feed/',
    'https://slack.engineering/feed/',
    'https://dropbox.tech/feed',
    'https://medium.com/feed/airbnb-engineering',
    'https://huggingface.co/blog/feed.xml',
    'https://pytorch.org/blog/feed.xml',
    'https://blog.tensorflow.org/feeds/posts/default?alt=rss',
    'https://openai.com/news/rss.xml',
    'https://www.cncf.io/feed/',
    'https://feed.infoq.com/development/',
    'https://feed.infoq.com/ai-ml-data-eng/news/',
    'https://feed.infoq.com/devops/news/',
    'https://aws.amazon.com/blogs/architecture/feed/',
    'https://aws.amazon.com/blogs/machine-learning/feed/',
    'https://cloud.google.com/blog/rss',
    'https://devblogs.microsoft.com/python/feed/',
    'https://tech.meituan.com/feed/',
    'https://www.ruanyifeng.com/blog/atom.xml',
    'https://www.oschina.net/news/rss',
]
TECH_ARTICLE_WRITER_SKILL_PATH = (
    Path(__file__).resolve().parents[1]
    / 'skills'
    / 'technical_article_writer'
    / 'SKILL.md'
)


@dataclass
class CollectorResult:
    created: int = 0
    skipped: int = 0
    failed: int = 0


def fetch_url(url, timeout=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; BlogCollector/1.0; +https://github.com/jeffryqueenie-coder/djangoblog)'
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_aihot_items(html, base_url=AIHOT_URL):
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.select('article, [class*="card"], [class*="item"], li')
    seen = set()
    items = []

    for card in cards:
        link = card.find('a', href=True)
        if not link:
            continue
        href = urljoin(base_url, link['href'])
        title = normalize_text(link.get_text(' ', strip=True))
        if not title or href in seen or len(title) < 4:
            continue

        text = normalize_text(card.get_text(' ', strip=True))
        summary = text.replace(title, '', 1).strip()
        tags = [normalize_text(tag.get_text(' ', strip=True)) for tag in card.select('[class*="tag"], .badge')]
        items.append({
            'title': title[:300],
            'summary': summary[:1200],
            'reason': '',
            'source': 'aihot',
            'source_name': 'AI HOT',
            'source_url': href,
            'tags': ','.join(tag for tag in tags if tag)[:300],
            'published_at': timezone.now(),
        })
        seen.add(href)

    return items


def collect_aihot_news(limit=30, hours=None):
    html = fetch_url(AIHOT_URL)
    items = parse_aihot_items(html)[:limit]
    cutoff = timezone.now() - timezone.timedelta(hours=hours) if hours else None
    result = CollectorResult()

    for item in items:
        if cutoff and item.get('published_at') and item['published_at'] < cutoff:
            result.skipped += 1
            continue
        try:
            source_url_hash = hash_url(item['source_url'])
            _, created = NewsItem.objects.update_or_create(
                source_url_hash=source_url_hash,
                defaults=item,
            )
            if created:
                result.created += 1
            else:
                result.skipped += 1
        except Exception:
            logger.exception('Failed to store AI HOT news: %s', item.get('source_url'))
            result.failed += 1

    cache.clear()
    return result


def parse_feed_entries(xml_text, source_url):
    root = ET.fromstring(xml_text)
    entries = []

    if root.tag.endswith('rss'):
        channel = root.find('.//channel')
        source_name = child_text(channel, 'title') if channel is not None else source_url
        for item in root.findall('.//channel/item'):
            entries.append({
                'title': normalize_text(child_text(item, 'title')),
                'url': normalize_text(child_text(item, 'link')),
                'summary': strip_html(child_text(item, 'description')),
                'published_at': parse_datetime(child_text(item, 'pubDate')),
                'source_name': source_name or source_url,
            })
        return entries

    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    source_name = child_text(root, 'title') or source_url
    for entry in root.findall('.//atom:entry', ns):
        link = entry.find('atom:link[@rel="alternate"]', ns) or entry.find('atom:link', ns)
        entries.append({
            'title': normalize_text(child_text(entry, 'title')),
            'url': normalize_text(link.get('href') if link is not None else ''),
            'summary': strip_html(child_text(entry, 'summary') or child_text(entry, 'content')),
            'published_at': parse_datetime(child_text(entry, 'updated') or child_text(entry, 'published')),
            'source_name': source_name,
        })
    return entries


def collect_tech_articles(limit=5, feeds=None, hours=None):
    feeds = feeds or parse_feed_list()
    cutoff = timezone.now() - timezone.timedelta(hours=hours) if hours else None
    result = CollectorResult()
    entries_by_url = {}

    for feed_url in feeds:
        try:
            entries = parse_feed_entries(fetch_url(feed_url), feed_url)
        except Exception:
            logger.exception('Failed to fetch or parse feed: %s', feed_url)
            result.failed += 1
            continue

        for entry in entries:
            if not entry['title'] or not entry['url']:
                result.skipped += 1
                continue
            published_at = entry_published_at(entry)
            if cutoff and published_at and published_at < cutoff:
                result.skipped += 1
                continue
            entry['published_at'] = published_at
            entries_by_url.setdefault(entry['url'], entry)

    for entry in sort_feed_entries(entries_by_url.values()):
        if result.created >= limit:
            break
        if Article.objects.filter(body__contains=entry['url']).exists():
            result.skipped += 1
            continue
        rewritten = rewrite_article(entry)
        if not rewritten:
            result.skipped += 1
            continue
        try:
            publish_rewritten_article(entry, rewritten)
            result.created += 1
        except IntegrityError:
            result.skipped += 1
        except Exception:
            logger.exception('Failed to publish rewritten article: %s', entry['url'])
            result.failed += 1

    cache.clear()
    return result


def rewrite_article(entry):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return ''

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get('OPENAI_BASE_URL') or None,
        )
        response = client.chat.completions.create(
            model=os.environ.get('BLOG_LLM_MODEL', 'gpt-4o-mini'),
            messages=[
                {
                    'role': 'system',
                    'content': load_technical_writer_skill(),
                },
                {
                    'role': 'user',
                    'content': (
                        f"来源标题：{entry['title']}\n"
                        f"来源摘要：{entry['summary']}\n\n"
                        "请按 skill 要求写成一篇完整中文技术文章。"
                        "必须包含至少一个和主题相关、可复制运行或改造的代码/命令/YAML 示例。"
                    )
                },
            ],
            temperature=0.4,
        )
        if getattr(response, 'usage', None):
            logger.info(
                'LLM usage for %s: prompt=%s completion=%s total=%s',
                entry.get('url'),
                getattr(response.usage, 'prompt_tokens', None),
                getattr(response.usage, 'completion_tokens', None),
                getattr(response.usage, 'total_tokens', None),
            )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception('Failed to rewrite article with LLM: %s', entry.get('url'))
        return ''


def publish_rewritten_article(entry, body):
    category, _ = Category.objects.get_or_create(name='文章')
    author = get_default_author()
    body = strip_source_link_lines(body)
    title = extract_markdown_title(body) or entry['title']
    body = strip_leading_markdown_title(body, title)
    article = Article.objects.create(
        title=title[:200],
        body=append_source_link(body, entry['url']),
        pub_time=normalize_model_datetime(entry['published_at']) or timezone.now(),
        status='p',
        type='a',
        comment_status='c',
        author=author,
        category=category,
    )
    return article


def load_technical_writer_skill():
    try:
        return TECH_ARTICLE_WRITER_SKILL_PATH.read_text(encoding='utf-8')
    except OSError:
        logger.warning('Technical writer skill not found: %s', TECH_ARTICLE_WRITER_SKILL_PATH)
        return (
            '你是技术博客作者。基于给定信息写一篇中文技术文章。'
            '输出 Markdown，包含具体分析和至少一个可复制的代码或命令示例。'
            '不能编造来源没有的信息，不要输出原文链接。'
        )


def get_default_author():
    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    if user:
        return user
    return User.objects.create_superuser('admin', 'admin@example.com', 'admin123')


def run_collectors_loop(interval=1800):
    while True:
        news_result = collect_aihot_news(
            limit=get_env_int('AIHOT_NEWS_LIMIT', 30),
            hours=get_optional_env_int('AIHOT_NEWS_LOOKBACK_HOURS'),
        )
        article_result = collect_tech_articles(
            limit=get_env_int('TECH_ARTICLE_LIMIT', 5),
            hours=get_optional_env_int('TECH_ARTICLE_LOOKBACK_HOURS'),
        )
        logger.info(
            'Collectors finished: news created=%s skipped=%s failed=%s; articles created=%s skipped=%s failed=%s',
            news_result.created,
            news_result.skipped,
            news_result.failed,
            article_result.created,
            article_result.skipped,
            article_result.failed,
        )
        time.sleep(interval)


def parse_feed_list():
    raw = os.environ.get('TECH_BLOG_FEEDS', '')
    if not raw:
        return DEFAULT_TECH_FEEDS
    return [item.strip() for item in raw.split(',') if item.strip()]


def sort_feed_entries(entries):
    return sorted(entries, key=feed_entry_timestamp, reverse=True)


def feed_entry_timestamp(entry):
    published_at = entry_published_at(entry)
    if not published_at:
        return 0
    return published_at.timestamp()


def entry_published_at(entry):
    return normalize_aware_datetime(entry.get('published_at'))


def normalize_aware_datetime(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def get_env_int(name, default):
    value = os.environ.get(name)
    if value in (None, ''):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        logger.warning('Invalid integer env %s=%r, using %s', name, value, default)
        return default
    return parsed if parsed > 0 else default


def get_optional_env_int(name):
    value = os.environ.get(name)
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        logger.warning('Invalid integer env %s=%r, ignoring it', name, value)
        return None
    return parsed if parsed > 0 else None


def child_text(node, name):
    child = node.find(name)
    if child is not None and child.text:
        return child.text.strip()
    for child in list(node):
        if child.tag.endswith(name) and child.text:
            return child.text.strip()
    return ''


def parse_datetime(value):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        try:
            parsed = timezone.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    return normalize_aware_datetime(parsed)


def strip_html(value):
    return normalize_text(BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True))


def normalize_text(value):
    return re.sub(r'\s+', ' ', unescape(value or '')).strip()


def hash_url(url):
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def normalize_model_datetime(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        return timezone.make_naive(value, timezone.get_current_timezone())
    return value


def strip_source_link_lines(body):
    lines = []
    for line in body.splitlines():
        normalized = line.strip().lower()
        if re.search(r'\[?原文链接\]?|原文[:：]|source\s*link|original\s*link', normalized):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()


def extract_source_url(body):
    for line in reversed(body.splitlines()):
        markdown_match = re.search(r'\[原文链接\]\((https?://[^)\s]+)\)', line)
        if markdown_match:
            return markdown_match.group(1)
        plain_match = re.search(r'原文链接[:：]\s*(https?://\S+)', line)
        if plain_match:
            return plain_match.group(1).rstrip('。.,，')
    return ''


def append_source_link(body, url):
    body = strip_source_link_lines(body)
    if not url:
        return body
    return f"{body}\n\n---\n[原文链接]({url})"


def extract_markdown_title(body):
    for line in body.splitlines():
        match = re.match(r'^\s*#\s+(.+?)\s*#*\s*$', line)
        if match:
            return normalize_text(match.group(1))
    return ''


def strip_leading_markdown_title(body, title):
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r'^\s*#\s+', lines[0]):
        heading = normalize_text(re.sub(r'^\s*#\s+', '', lines[0]).strip(' #'))
        if not title or heading == title:
            lines.pop(0)
    return '\n'.join(lines).strip()
