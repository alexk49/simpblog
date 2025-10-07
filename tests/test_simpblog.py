import unittest
import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from simpblog import HTMLFile, simpblog


class TestHTMLFile(unittest.TestCase):
    def test_htmlfile_creation_and_metadata(self):
        metadata = {"title": "Test Post"}
        html = HTMLFile("<p>hello</p>", metadata)
        self.assertIsInstance(html, HTMLFile)
        self.assertEqual(html, "<p>hello</p>")
        self.assertEqual(html.metadata, metadata)


class Testsimpblog(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.posts_dir = os.path.join(self.temp_dir, "posts")
        self.pages_dir = os.path.join(self.temp_dir, "pages")
        self.templates_dir = os.path.join(self.temp_dir, "templates")
        self.static_dir = os.path.join(self.temp_dir, "static")
        self.output_dir = os.path.join(self.temp_dir, "output")

        os.makedirs(self.posts_dir)
        os.makedirs(self.pages_dir)
        os.makedirs(self.templates_dir)
        os.makedirs(self.static_dir)
        os.makedirs(self.output_dir)

        self.gen = simpblog(
            posts_dir=self.posts_dir,
            pages_dir=self.pages_dir,
            templates_dir=self.templates_dir,
            static_dir=self.static_dir,
            output_dir=self.output_dir,
        )

        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Rendered</html>"
        self.gen.templates_env.get_template = MagicMock(return_value=mock_template)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_get_posts_htmlfile(self):
        # Create a fake HTML post
        post_path = os.path.join(self.posts_dir, "test.html")
        with open(post_path, "w") as f:
            f.write("<p>hi</p>")

        self.gen.get_posts()

        self.assertIn("test.html", self.gen.posts)
        post = self.gen.posts["test.html"]
        self.assertIsInstance(post, HTMLFile)
        self.assertIn("title", post.metadata)
        self.assertIn("date", post.metadata)

    def test_sort_posts_by_date(self):
        post1 = HTMLFile("a", {"date": "2024-01-01"})
        post2 = HTMLFile("b", {"date": "2025-01-01"})
        self.gen.posts = {"a.html": post1, "b.html": post2}

        self.gen.sort_posts()
        sorted_keys = list(self.gen.posts.keys())
        self.assertEqual(sorted_keys, ["b.html", "a.html"])

    def test_get_post_date_returns_datetime(self):
        post = HTMLFile("content", {"date": "2023-02-10"})
        self.gen.posts["p.html"] = post
        result = self.gen.get_post_date("p.html")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2023)

    def test_render_page_returns_tuple(self):
        page = HTMLFile("<p>page</p>", {"title": "About", "slug": "about"})
        self.gen.pages["about.html"] = page
        slug, html = self.gen.render_page("about.html")
        self.assertEqual(slug, "about")
        self.assertIn("Rendered", html)

    def test_render_post_page_missing_metadata_raises(self):
        self.gen.posts["bad.html"] = HTMLFile("<p>oops</p>", {"title": "x"})
        with self.assertRaises(ValueError):
            self.gen.render_post_page("bad.html")

    def test_render_post_page_success(self):
        meta = {"title": "Good", "date": "2023-01-01", "slug": "good", "tags": ""}
        self.gen.posts["good.html"] = HTMLFile("<p>ok</p>", meta)
        slug, html = self.gen.render_post_page("good.html")
        self.assertEqual(slug, "good")
        self.assertIn("Rendered", html)

    def test_check_for_changes_triggers_on_missing_output(self):
        src = os.path.join(self.temp_dir, "src.txt")
        dst = os.path.join(self.temp_dir, "dst.txt")
        with open(src, "w") as f:
            f.write("x")

        result = self.gen.check_for_changes(src, dst)
        self.assertTrue(result)

    def test_check_for_changes_skips_when_up_to_date(self):
        src = os.path.join(self.temp_dir, "src.txt")
        dst = os.path.join(self.temp_dir, "dst.txt")
        with open(src, "w") as f:
            f.write("src")
        shutil.copy2(src, dst)

        result = self.gen.check_for_changes(src, dst)
        self.assertFalse(result)

    def test_write_file_creates_and_writes(self):
        file_path = os.path.join(self.output_dir, "test.html")
        self.gen.write_file(file_path, "hello world")
        with open(file_path) as f:
            self.assertEqual(f.read(), "hello world")

    def test_get_tags_collects_unique_sorted_tags(self):
        self.gen.posts = {
            "1.html": HTMLFile("x", {"tags": "python, test"}),
            "2.html": HTMLFile("y", {"tags": "test, ai"}),
        }
        tags = self.gen.get_tags()
        self.assertEqual(tags, ["ai", "python", "test"])

    def test_check_homepage_conflict_raises(self):
        open(os.path.join(self.pages_dir, "index.html"), "w").close()
        open(os.path.join(self.templates_dir, "index.html"), "w").close()
        with self.assertRaises(RuntimeError):
            self.gen.check_homepage_paths()

    def test_check_homepage_content_exists(self):
        open(os.path.join(self.pages_dir, "index.html"), "w").close()
        self.assertTrue(self.gen.check_homepage_paths())

    def test_copy_static_copies_files(self):
        src_file = os.path.join(self.static_dir, "file.txt")
        with open(src_file, "w") as f:
            f.write("static data")

        with patch.object(self.gen, "check_for_changes", return_value=True):
            self.gen.copy_static()

        dst_file = os.path.join(self.output_dir, "static", "file.txt")
        self.assertTrue(os.path.exists(dst_file))
        with open(dst_file) as f:
            self.assertEqual(f.read(), "static data")


if __name__ == "__main__":
    unittest.main()
