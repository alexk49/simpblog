import os
import shutil
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
    ):

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
            filepath = os.path.join(self.posts_dir, markdown_post)

            with open(filepath, "r") as file:
                self.posts[markdown_post] = markdown(file.read(), extras=["metadata", "fenced-code-blocks"])

        self.sort_posts()

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

        post_data = {
            "title": post_metadata["title"],
            "date": post_metadata["date"],
            "content": self.posts[post_key],
        }

        post_template = self.templates_env.get_template("post.html")
        post_html = post_template.render(post=post_data)

        return post_metadata["slug"], post_html

    def generate_site(self):
        """
        Generate the static site, including homepage, posts, and tag pages.
        """
        self.get_posts()

        home_html = self.render_homepage()
        home_output_path = os.path.join(self.output_dir, "index.html")
        self.write_file(home_output_path, home_html)

        unique_tags = set()

        for post_key in self.posts:
            slug, post_html = self.render_post_page(post_key)
            post_file_path = os.path.join(self.output_dir, "posts", f"{slug}.html")
            self.write_file(post_file_path, post_html)

            unique_tags.update(
                tag.strip() for tag in self.posts[post_key].metadata["tags"].split(",")
            )

        sorted_tags = sorted(unique_tags)

        for tag in sorted_tags:
            print(tag)
            tag_html = self.render_tag_page(tag)
            tag_file_path = os.path.join(self.output_dir, "tags", f"{tag}.html")
            self.write_file(tag_file_path, tag_html)

        shutil.copytree(self.static_dir, os.path.join(self.output_dir, "static"), dirs_exist_ok=True)

    @staticmethod
    def write_file(file_path, content):
        """
        Write content to a file, creating directories as needed.

        :param file_path: The path to the file to write.
        :param content: The content to write to the file.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            file.write(content)


def main():
    ssg = SimpleSiteGenerator()

    ssg.generate_site()


if __name__ == "__main__":
    main()
