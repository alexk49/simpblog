#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from markdown2 import markdown


class HTMLFile(str):
    """handle html files like markdown files"""
    def __new__(cls, value, metadata):
        obj = str.__new__(cls, value)
        obj.metadata = metadata
        return obj


class simpblog:
    def __init__(
        self,
        posts_dir: str = "posts",
        pages_dir: str = "pages",
        output_dir: str = "output",
        templates_dir: str = "templates",
        static_dir: str = "static",
        full_rebuild: bool = False,
    ):

        self.full_rebuild = full_rebuild

        self.posts_dir = posts_dir
        self.pages_dir = pages_dir
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        self.output_dir = output_dir

        templateLoader = FileSystemLoader(searchpath=self.templates_dir)
        self.templates_env = Environment(loader=templateLoader)

        self.posts: dict = {}
        self.pages: dict = {}

    def get_posts(self):
        if not os.path.exists(self.posts_dir):
            print(f"no posts dir found at {self.posts_dir}")
            return

        for post_file in os.listdir(self.posts_dir):
            if not (post_file.endswith(".md") or post_file.endswith(".html")):
                continue

            filepath = os.path.join(self.posts_dir, post_file)
            with open(filepath, "r") as file:
                content = file.read()

            if post_file.endswith(".md"):
                post_content = markdown(content, extras=["metadata", "fenced-code-blocks"])
            else:
                html_metadata = {
                    "title": os.path.splitext(post_file)[0].replace("-", " ").title(),
                    "date": datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d"),
                    "slug": os.path.splitext(post_file)[0],
                    "tags": "",
                }

                post_content = HTMLFile(content, html_metadata)

            self.posts[post_file] = post_content

    def sort_posts(self):
        sorted_posts = sorted(self.posts, key=self.get_post_date, reverse=True)
        self.posts = {post: self.posts[post] for post in sorted_posts}

    def get_post_date(self, post: str) -> datetime:
        # Extracts and parses the date for sorting
        return datetime.strptime(self.posts[post].metadata["date"], "%Y-%m-%d")

    def get_pages(self):
        if not os.path.exists(self.pages_dir):
            return

        for page_file in os.listdir(self.pages_dir):
            if not (page_file.endswith(".md") or page_file.endswith(".html")):
                continue

            filepath = os.path.join(self.pages_dir, page_file)
            with open(filepath, "r") as file:
                content = file.read()

            if page_file.endswith(".md"):
                page_content = markdown(content, extras=["metadata", "fenced-code-blocks"])
            else:
                html_metadata = {
                    "title": os.path.splitext(page_file)[0].replace("-", " ").title(),
                    "slug": os.path.splitext(page_file)[0],
                }

                page_content = HTMLFile(content, html_metadata)

            self.pages[page_file] = page_content

    def render_page(self, page_key: str) -> tuple[str, str]:
        """
        render an individual static page - about etc
        """
        page_metadata = self.pages[page_key].metadata
        page_data = {
            "title": page_metadata.get("title"),
            "slug": page_metadata.get("slug"),
            "content": self.pages[page_key],
        }

        page_template = self.templates_env.get_template("page.html")
        page_html = page_template.render(page=page_data)
        return page_metadata.get("slug", "page"), page_html

    def render_homepage(self) -> str:
        """
        Create homepage, returns rendered html
        """
        home_template = self.templates_env.get_template("index.html")
        posts_metadata = [self.posts[post].metadata for post in self.posts]

        return home_template.render(posts=posts_metadata)

    def render_tag_page(self, tag: str) -> str:
        """
        Render a page for a specific tag, listing all posts with that tag.

        And, return rendered HTML for the tag page.
        """
        tag_template = self.templates_env.get_template("tag.html")
        posts_with_tag = [
            post_content.metadata
            for post_content in self.posts.values()
            if tag in post_content.metadata["tags"]
        ]
        return tag_template.render(tag=tag, posts=posts_with_tag)

    def render_post_page(self, post_key: str) -> tuple[str, str]:
        """
        Render an individual post page.

        :param post_key: The key of the post in the self.posts dictionary.
        :return: A tuple of (slug, rendered HTML for the post).
        """
        post_metadata = self.posts[post_key].metadata
        required = ["title", "date", "slug"]

        for key in required:
            if key not in post_metadata:
                raise ValueError(f"Missing required metadata '{key}' in {post_key}")

        post_data = {
            "title": post_metadata["title"],
            "date": post_metadata["date"],
            "tags": post_metadata["tags"],
            "content": self.posts[post_key],
        }

        post_template = self.templates_env.get_template("post.html")
        post_html = post_template.render(post=post_data)

        return post_metadata["slug"], post_html

    def copy_static(self):
        """
        copy static files if missing or newer
        """
        if not os.path.exists(self.static_dir):
            print(f"no static dir found to copy at {self.static_dir}")
            return

        output_static = os.path.join(self.output_dir, "static")
        os.makedirs(output_static, exist_ok=True)

        for root, _, files in os.walk(self.static_dir):
            for file in files:
                src = os.path.join(root, file)
                rel_path = os.path.relpath(src, self.static_dir)
                dst = os.path.join(output_static, rel_path)

                os.makedirs(os.path.dirname(dst), exist_ok=True)

                if self.check_for_changes(src, dst):
                    shutil.copy2(src, dst)

    def write_homepage(self, layout_path: str):
        homepage_template_path = os.path.join(self.templates_dir, "index.html")
        if not os.path.exists(homepage_template_path):
            print(f"index.html page not found in {self.templates_dir}")
            return

        home_html = self.render_homepage()
        homepage_output_path = os.path.join(self.output_dir, "index.html")

        self.write_file(homepage_output_path, home_html, source_paths=[homepage_template_path, layout_path])

    def write_pages(self, page_template_path: str, layout_path: str):
        if not os.path.exists(page_template_path):
            print(f"no page template path at: {page_template_path}")
            return

        print("writing pages")

        for page_key in self.pages:
            slug, page_html = self.render_page(page_key)

            if slug == "index":
                page_file_path = os.path.join(self.output_dir, "index.html")
            else:
                page_file_path = os.path.join(self.output_dir, f"{slug}.html")

            source_paths = [
                os.path.join(self.pages_dir, page_key),
                page_template_path,
                layout_path,
            ]
            self.write_file(page_file_path, page_html, source_paths=source_paths)

    def write_post_pages(self, post_template_path: str, layout_path: str):
        if not os.path.exists(post_template_path):
            print(f"no post template found at: {post_template_path}")
            return

        print("creating posts")

        for post_key in self.posts:
            slug, post_html = self.render_post_page(post_key)
            post_file_path = os.path.join(self.output_dir, "posts", f"{slug}.html")

            source_paths = [
                os.path.join(self.posts_dir, post_key),
                post_template_path,
                layout_path,
            ]

            self.write_file(post_file_path, post_html, source_paths=source_paths)

    def get_tags(self) -> set:
        unique_tags = set()
        print("searching for tags")

        for post_key in self.posts:
            unique_tags.update(
                tag.strip() for tag in self.posts[post_key].metadata["tags"].split(",")
            )
        sorted_tags = sorted(unique_tags)
        return sorted_tags

    def write_tag_pages(self, tags: set, layout_path: str):
        tag_template_path = os.path.join(self.templates_dir, "tag.html")

        for tag in tags:
            print(f"checking for changes for {tag}")
            tag_html = self.render_tag_page(tag)
            tag_file_path = os.path.join(self.output_dir, "tags", f"{tag}.html")

            # Check dependencies for tag pages — template, layout, and all posts
            # as tags are generated from post front matter
            post_sources = [os.path.join(self.posts_dir, p) for p in self.posts]
            source_paths = [tag_template_path, layout_path] + post_sources

            self.write_file(tag_file_path, tag_html, source_paths=source_paths)

    def check_homepage_paths(self) -> bool:
        """
        homepage can be either templates/index.html or in pages

        check for conflicts if both
        """
        homepage_content_path_md = os.path.join(self.pages_dir, "index.md")
        homepage_content_path_html = os.path.join(self.pages_dir, "index.html")
        homepage_template_path = os.path.join(self.templates_dir, "index.html")

        content_homepage_exists = (
            os.path.exists(homepage_content_path_md)
            or os.path.exists(homepage_content_path_html)
        )
        template_homepage_exists = os.path.exists(homepage_template_path)

        if content_homepage_exists and template_homepage_exists:
            raise RuntimeError(
                f"Conflict: both a content homepage (pages/index.*) and "
                f"a template homepage ({homepage_template_path}) exist. "
                f"Please remove one."
            )
        return content_homepage_exists

    def generate_site(self):
        """
        Generate the static site, including homepage, pages, posts, and tag pages.
        """
        layout_path = os.path.join(self.templates_dir, "layout.html")

        self.get_posts()
        self.sort_posts()
        self.get_pages()

        content_homepage_exists = self.check_homepage_paths()
        if not content_homepage_exists:
            self.write_homepage(layout_path)

        page_template_path = os.path.join(self.templates_dir, "page.html")

        self.write_pages(page_template_path=page_template_path, layout_path=layout_path)

        post_template_path = os.path.join(self.templates_dir, "post.html")

        self.write_post_pages(post_template_path=post_template_path, layout_path=layout_path)

        tags = self.get_tags()
        self.write_tag_pages(tags=tags, layout_path=layout_path)

        self.copy_static()

        print(f"Site generated with {len(self.posts)} posts, {len(tags)} tags.")

    def write_file(self, file_path: str, content: str, source_paths: list | str | None = None):
        """
        Write content to a file, creating directories as needed.
        Only writes if the source is newer (when source_paths are provided).
        """
        if source_paths and not self.check_for_changes(source_paths, file_path):
            print(f"No changes detected for {file_path}")
            return

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        print(f"writing file to {file_path}")
        with open(file_path, "w") as file:
            file.write(content)

    def check_for_changes(self, source_paths: list | str | None, output_path: str) -> bool:
        """
        Check if output needs to be rebuilt based on modification times.

        :param source_paths: A single path or list/tuple of source files.
        :param output_path: Path to the generated file in output.
        :return: True if rebuild needed, False otherwise.
        """
        if self.full_rebuild:
            return True

        if isinstance(source_paths, (str, os.PathLike)):
            source_paths = [source_paths]

        if not os.path.exists(output_path):
            print(f"no output path exists at {output_path}, building file")
            return True

        for src in source_paths:
            if not os.path.exists(src):
                print(f"source not found ({src}), forcing rebuild")
                return True

            if os.path.getmtime(src) > os.path.getmtime(output_path):
                print(f"{src} is newer than {output_path}, rebuilding")
                return True

        return False


def start_dev_server(directory: str, port: int = 8000):
    os.chdir(directory)
    handler = SimpleHTTPRequestHandler
    httpd = TCPServer(("localhost", port), handler)

    print(f"Serving at http://localhost:{port} (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server...")
    finally:
        httpd.server_close()


def inotifywait_exists() -> bool:
    return shutil.which("inotifywait") is not None


def watch_with_inotify(dir_paths: dict[str, str], simpblog: simpblog):
    """Use inotifywait to rebuild when files change."""
    print("Watching for changes in pages/, posts/, templates/, and static/")

    watch_paths = [
        dir_paths[key]
        for key in ("pages_dir", "posts_dir", "templates_dir", "static_dir")
        if os.path.exists(dir_paths[key])
    ]

    if not watch_paths:
        print("No watchable directories found.")
        return

    cmd = ["inotifywait", "-m", "-r", "-e", "modify,create,delete"] + watch_paths
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            print(f"Change detected: {line}")
            try:
                simpblog.generate_site()
            except subprocess.CalledProcessError as e:
                print(f"Build failed: {e}")
    except KeyboardInterrupt:
        print("Stopping watcher...")
        process.terminate()


def run_dev(dir_paths: dict[str, str], port: int, simpblog: simpblog):
    server_thread = threading.Thread(
        target=start_dev_server, args=(dir_paths["output_dir"], port), daemon=True
    )
    server_thread.start()

    if inotifywait_exists():
        print("Detected inotifywait: enabling file watching\n")
        watch_with_inotify(dir_paths, simpblog)
    else:
        print("inotifywait not found. Skipping auto-rebuild.")
        print("Dev server running at http://localhost:8000 (Ctrl+C to stop)\n")

        try:
            while server_thread.is_alive():
                server_thread.join(1)
        except KeyboardInterrupt:
            print("\nStopping dev server...")


def set_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple static site generator")

    parser.add_argument(
        "-s",
        "--site-dir",
        type=str,
        default=".",
        help="Root directory for site content (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force full rebuild even if files haven't changed",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        default=False,
        help="Run build, start dev server, and optionally watch for changes",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the dev server (default: 8000)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Run tests",
    )
    return parser


def main():
    parser = set_arg_parser()
    args = parser.parse_args()

    if args.test:
        cmd = ["python", "-m", "unittest", "discover", "-v"]
        subprocess.run(cmd, check=True)
        return

    site_dir = os.path.abspath(args.site_dir)

    dir_paths = {
        "posts_dir": os.path.join(site_dir, "posts"),
        "pages_dir": os.path.join(site_dir, "pages"),
        "templates_dir": os.path.join(site_dir, "templates"),
        "static_dir": os.path.join(site_dir, "static"),
        "output_dir": os.path.join(site_dir, "output"),
    }

    print(f"Building site from: {site_dir} to {dir_paths["output_dir"]}")

    simpblog = simpblog(
        posts_dir=dir_paths["posts_dir"],
        pages_dir=dir_paths["pages_dir"],
        output_dir=dir_paths["output_dir"],
        templates_dir=dir_paths["templates_dir"],
        static_dir=dir_paths["static_dir"],
        full_rebuild=args.force,
    )

    simpblog.generate_site()

    if args.dev:
        run_dev(dir_paths, args.port, simpblog)



if __name__ == "__main__":
    main()
