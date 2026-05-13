import os
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from blog.services.collectors import (
    DEFAULT_TECH_FEEDS,
    get_env_int,
    get_optional_env_int,
    parse_feed_entries,
    parse_feed_list,
    sort_feed_entries,
)


class FeedCollectorParsingTest(SimpleTestCase):
    def test_parse_rss_entries_uses_channel_title_and_pubdate(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Example Engineering</title>
            <item>
              <title>Scaling Django Workers</title>
              <link>https://example.com/django-workers</link>
              <description><![CDATA[<p>Worker queue tuning notes.</p>]]></description>
              <pubDate>Wed, 13 May 2026 10:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        entries = parse_feed_entries(xml, 'https://example.com/feed.xml')

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['title'], 'Scaling Django Workers')
        self.assertEqual(entries[0]['source_name'], 'Example Engineering')
        self.assertEqual(entries[0]['summary'], 'Worker queue tuning notes.')
        self.assertEqual(entries[0]['published_at'].year, 2026)

    def test_parse_atom_entries_uses_feed_title_and_updated_time(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>AI Framework Blog</title>
          <entry>
            <title>New Inference Runtime</title>
            <link href="https://example.com/runtime" rel="alternate" />
            <summary>Runtime changes for model serving.</summary>
            <updated>2026-05-12T08:30:00+00:00</updated>
          </entry>
        </feed>
        """

        entries = parse_feed_entries(xml, 'https://example.com/atom.xml')

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['title'], 'New Inference Runtime')
        self.assertEqual(entries[0]['source_name'], 'AI Framework Blog')
        self.assertEqual(entries[0]['url'], 'https://example.com/runtime')
        self.assertEqual(entries[0]['published_at'].day, 12)

    def test_sort_feed_entries_newest_first_with_missing_dates_last(self):
        older = datetime(2026, 5, 11, tzinfo=datetime_timezone.utc)
        newer = datetime(2026, 5, 13, tzinfo=datetime_timezone.utc)
        entries = [
            {'title': 'missing'},
            {'title': 'older', 'published_at': older},
            {'title': 'newer', 'published_at': newer},
        ]

        sorted_entries = sort_feed_entries(entries)

        self.assertEqual([entry['title'] for entry in sorted_entries], ['newer', 'older', 'missing'])


class FeedCollectorConfigTest(SimpleTestCase):
    @patch.dict(os.environ, {'TECH_BLOG_FEEDS': ''}, clear=False)
    def test_parse_feed_list_uses_default_feeds(self):
        self.assertEqual(parse_feed_list(), DEFAULT_TECH_FEEDS)
        self.assertGreaterEqual(len(DEFAULT_TECH_FEEDS), 20)

    @patch.dict(os.environ, {'TECH_BLOG_FEEDS': ' https://a.test/feed.xml,https://b.test/rss '}, clear=False)
    def test_parse_feed_list_uses_env_feeds(self):
        self.assertEqual(parse_feed_list(), ['https://a.test/feed.xml', 'https://b.test/rss'])

    @patch.dict(os.environ, {'TECH_ARTICLE_LIMIT': '12', 'BAD_INT': 'abc'}, clear=False)
    def test_env_int_helpers(self):
        self.assertEqual(get_env_int('TECH_ARTICLE_LIMIT', 5), 12)
        self.assertEqual(get_env_int('BAD_INT', 5), 5)
        self.assertIsNone(get_optional_env_int('MISSING_INT'))
