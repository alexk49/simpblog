import argparse
import os
import shutil
import time
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from markdown2 import markdown


class SimpleSiteGenerator:
    def __init__(
        self,
        posts_dir="posts",
        output_dir="output",
        templates_dir="templates",
        static_dir="static",
        full_rebuild=False,
    ):

        self.full_rebuild = full_rebuild

        self.posts_dir = posts_dir
        self.static_dir = static_dir
        self.output_dir = output_dir

        if os.path.exists(self.output_dir) is False:
            os.mkdir(self.output_dir)

        templateLoader = FileSystemLoader(searchpath=templates_dir)

        self.templates_env = Environment(loader=templateLoader)

        self.posts = {}

    def get_posts(self):
        """
        Get post markdown files from posts directory
        """
        for markdown_post in os.listdir(self.posts_dir):
            if not markdown_post.endswith(".md"):
                continue

            filepath = os.path.join(self.posts_dir, markdown_post)

            with open(filepath, "r") as file:
                self.posts[markdown_post] = markdown(file.read(), extras=["metadata", "fenced-code-blocks"])

    def sort_posts(self):
        """
        Sort posts in date order
        """
        sorted_posts = sorted(self.posts, key=self.get_post_date, reverse=True)
        self.posts = {post: self.posts[post] for post in sorted_posts}

    def get_post_date(self, post):
        # Extracts and parses the date for sorting
        return datetime.strptime(self.posts[post].metadata["date"], "%Y-%m-%d")

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

                #if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                if self.check_for_changes(src, dst):
                    shutil.copy2(src, dst)

    def check_tag_for_changes(self, tag_template_path, tag_file_path) -> bool:
        """
        returns true if changes detected
        """
        if self.check_for_changes(tag_template_path, tag_file_path):
            return True

        # Check if any post is newer than tag page
        for post_key in self.posts:
            post_path = os.path.join(self.posts_dir, post_key)
            if self.check_for_changes(post_path, tag_file_path):
                return True
        return False

    def layout_recently_changed(self, minutes=1):
        layout_path = os.path.join("templates", "layout.html")
        if not os.path.exists(layout_path):
            return False

        mtime = os.path.getmtime(layout_path)
        now = time.time()
        return (now - mtime) < (minutes * 60)

    def generate_site(self):
        """
        Generate the static site, including homepage, posts, and tag pages.
        """
        if self.layout_recently_changed():
            print("layout changed forcing full rebuild")
            self.full_rebuild = True

        self.get_posts()
        self.sort_posts()

        home_html = self.render_homepage()
        home_output_path = os.path.join(self.output_dir, "index.html")

        home_template_path = os.path.join("templates", "index.html")
        self.write_file(home_output_path, home_html, source_path=home_template_path)

        unique_tags = set()

        for post_key in self.posts:
            slug, post_html = self.render_post_page(post_key)
            post_file_path = os.path.join(self.output_dir, "posts", f"{slug}.html")
            source_path = os.path.join(self.posts_dir, post_key)
            self.write_file(post_file_path, post_html, source_path=source_path)

            unique_tags.update(
                tag.strip() for tag in self.posts[post_key].metadata["tags"].split(",")
            )

        sorted_tags = sorted(unique_tags)
        tag_template_path = os.path.join("templates", "tag.html")

        for tag in sorted_tags:
            print(f"checking for changes for {tag}")
            tag_html = self.render_tag_page(tag)
            tag_file_path = os.path.join(self.output_dir, "tags", f"{tag}.html")

            if self.check_tag_for_changes(tag_template_path, tag_file_path):
                self.write_file(tag_file_path, tag_html)
            else:
                print(f"no changes detected for tag {tag}")

        self.copy_static()

        print(f"Site generated with {len(self.posts)} posts, {len(sorted_tags)} tags.")

    def write_file(self, file_path, content, source_path=None):
        """
        Write content to a file, creating directories as needed.
        Only writes if the source is newer (when a source_path is provided).

        :param file_path: The path to the file to write.
        :param content: The content to write to the file.
        :param source_path: Optional path to the source file
        """
        if source_path and not self.check_for_changes(source_path, file_path):
            print(f"No changes detected for {source_path}, leaving {file_path}")
            return

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        print(f"writing file to {file_path}")
        with open(file_path, "w") as file:
            file.write(content)

    def check_for_changes(self, source_path, output_path):
        """
        Check if output needs to be rebuilt based on file modification times.

        :param source_path: Path to the source file (markdown/template/etc.)
        :param output_path: Path to the generated file in output
        :return: True if rebuild needed, False otherwise
        """
        if self.full_rebuild:
            return True

        if not os.path.exists(output_path):
            print(f"no output path exists at {output_path}, building file")
            return True

        if not os.path.exists(source_path):
            print("no source path found, forcing rebuild")
            return True

        return os.path.getmtime(source_path) > os.path.getmtime(output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", default=False, help="Force full rebuild")
    args = parser.parse_args()

    ssg = SimpleSiteGenerator(full_rebuild=args.force)
    ssg.generate_site()


if __name__ == "__main__":
    main()
