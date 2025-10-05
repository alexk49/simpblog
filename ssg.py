import argparse
import os
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from markdown2 import markdown


class HTMLFile(str):
    """handle html files like markdown files"""
    def __new__(cls, value, metadata):
        obj = str.__new__(cls, value)
        obj.metadata = metadata
        return obj


class SimpleSiteGenerator:
    def __init__(
        self,
        posts_dir="posts",
        pages_dir="pages",
        output_dir="output",
        templates_dir="templates",
        static_dir="static",
        full_rebuild=False,
    ):

        self.full_rebuild = full_rebuild

        self.posts_dir = posts_dir
        self.pages_dir = pages_dir
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        self.output_dir = output_dir

        if os.path.exists(self.output_dir) is False:
            os.mkdir(self.output_dir)

        templateLoader = FileSystemLoader(searchpath=templates_dir)

        self.templates_env = Environment(loader=templateLoader)

        self.posts = {}
        self.pages = {}

    def get_posts(self):
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

    def get_post_date(self, post):
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

    def render_page(self, page_key):
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

    def render_homepage(self):
        """
        Create homepage, returns rendered html
        """
        home_template = self.templates_env.get_template("index.html")
        posts_metadata = [self.posts[post].metadata for post in self.posts]

        return home_template.render(posts=posts_metadata)

    def render_tag_page(self, tag):
        """
        Render a page for a specific tag, listing all posts with that tag.

        :param tag: The tag to render the page for.
        :return: Rendered HTML for the tag page.
        """
        tag_template = self.templates_env.get_template("tag.html")
        posts_with_tag = [
            post_content.metadata
            for post_content in self.posts.values()
            if tag in post_content.metadata["tags"]
        ]
        return tag_template.render(tag=tag, posts=posts_with_tag)

    def render_post_page(self, post_key):
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

    def generate_site(self):
        """
        Generate the static site, including homepage, pages, posts, and tag pages.
        """
        layout_path = os.path.join("templates", "layout.html")

        self.get_posts()
        self.sort_posts()
        self.get_pages()

        home_html = self.render_homepage()
        home_output_path = os.path.join(self.output_dir, "index.html")

        home_template_path = os.path.join("templates", "index.html")
        self.write_file(home_output_path, home_html, source_paths=[home_template_path, layout_path])

        print("writing pages")
        page_template_path = os.path.join("templates", "page.html")

        for page_key in self.pages:
            slug, page_html = self.render_page(page_key)
            page_file_path = os.path.join(self.output_dir, f"{slug}.html")

            source_paths = [
                os.path.join(self.pages_dir, page_key),
                page_template_path,
                layout_path,
            ]
            self.write_file(page_file_path, page_html, source_paths=source_paths)

        print("creating posts")
        unique_tags = set()
        post_template_path = os.path.join(self.templates_dir, "post.html")

        for post_key in self.posts:
            slug, post_html = self.render_post_page(post_key)
            post_file_path = os.path.join(self.output_dir, "posts", f"{slug}.html")

            source_paths = [
                os.path.join(self.posts_dir, post_key),
                post_template_path,
                layout_path,
            ]

            self.write_file(post_file_path, post_html, source_paths=source_paths)

            unique_tags.update(
                tag.strip() for tag in self.posts[post_key].metadata["tags"].split(",")
            )

        print("creating tag pages")
        sorted_tags = sorted(unique_tags)
        tag_template_path = os.path.join("templates", "tag.html")

        for tag in sorted_tags:
            print(f"checking for changes for {tag}")
            tag_html = self.render_tag_page(tag)
            tag_file_path = os.path.join(self.output_dir, "tags", f"{tag}.html")

            # Check dependencies for tag pages — template, layout, and all posts
            post_sources = [os.path.join(self.posts_dir, p) for p in self.posts]
            source_paths = [tag_template_path, layout_path] + post_sources

            self.write_file(tag_file_path, tag_html, source_paths=source_paths)

        self.copy_static()

        print(f"Site generated with {len(self.posts)} posts, {len(sorted_tags)} tags.")

    def write_file(self, file_path, content, source_paths=None):
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

    def check_for_changes(self, source_paths, output_path):
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

        # no rebuild needed
        return False


def main():
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
        help="Force full rebuild even if files haven't changed",
    )
    args = parser.parse_args()

    site_dir = os.path.abspath(args.site_dir)

    posts_dir = os.path.join(site_dir, "posts")
    pages_dir = os.path.join(site_dir, "pages")
    templates_dir = os.path.join(site_dir, "templates")
    static_dir = os.path.join(site_dir, "static")
    output_dir = os.path.join(site_dir, "output")

    print(f"Building site from: {site_dir}")
    print(f"posts: {posts_dir}")
    print(f"pages: {pages_dir}")
    print(f"templates: {templates_dir}")
    print(f"static: {static_dir}")
    print(f"output: {output_dir}")

    ssg = SimpleSiteGenerator(
        posts_dir=posts_dir,
        pages_dir=pages_dir,
        output_dir=output_dir,
        templates_dir=templates_dir,
        static_dir=static_dir,
        full_rebuild=args.force,
    )

    ssg.generate_site()

if __name__ == "__main__":
    main()
