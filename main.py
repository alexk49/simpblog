import os
import re

from jinja2 import Environment, PackageLoader
from markdown2 import markdown


POSTS_DIR = "posts"

POSTS = {}


def convert_markdown_files(directory_path):
    """Convert all md files in posts directory to html"""
    for file in os.listdir(directory_path):
        if file.endswith(".md"):
            file_path = os.path.join(directory_path, file)
            with open(file_path, "r", encoding="utf-8") as output:
                # metadata tag passes over variables at top of md file
                # as python dict
                html_post = markdown(output.read(), extras=["metadata"])
                POSTS[file] = html_post


def get_title(file_path):
    title_pattern = r"^#\s.*"
    title = ""
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        for line in lines:
            title = re.search(title_pattern, line)
            if title:
                title = title.group().replace("# ", "")
                break
        return title


def main():
    convert_markdown_files(POSTS_DIR)

    for post in POSTS:
        metadata = POSTS[post].metadata
        try:
            title = metadata["title"]
        except KeyError:
            file_path = os.path.join(POSTS_DIR, post)
            title = get_title(file_path)
            metadata["title"] = title

        print(title)


if __name__ == "__main__":
    main()

"""
for markdown_post in os.listdir("posts"):
    file_path = os.path.join("posts", markdown_post)

    with open(file_path, "r") as file:
        POSTS[markdown_post] = markdown(file.read(), extras=["metadata"])


POSTS = {
    post: POSTS[post]
    for post in sorted(
        POSTS,
        key=lambda post: datetime.strptime(POSTS[post].metadata["date"], "%Y-%m-%d"),
        reverse=True,
    )
}

env = Environment(loader=PackageLoader("main", "templates"))
home_template = env.get_template("index.html")
post_template = env.get_template("post.html")

posts_metadata = [POSTS[post].metadata for post in POSTS]
tags = [post["tags"] for post in posts_metadata]
home_html = home_template.render(posts=posts_metadata, tags=tags)

with open("site/index.html", "w") as file:
    file.write(home_html)

for post in POSTS:
    post_metadata = POSTS[post].metadata

    post_data = {
        "posts": POSTS[post],
        "title": post_metadata["title"],
        "date": post_metadata["date"],
    }

    post_html = post_template.render(post=post_data)
    post_file_path = "site/posts/{slug}.html".format(slug=post_metadata["slug"])

    os.makedirs(os.path.dirname(post_file_path), exist_ok=True)
    with open(post_file_path, "w") as file:
        file.write(post_html)
"""
