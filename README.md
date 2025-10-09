# simpblog

Simple static site generator that can be used to template the html/markdown for a simple blog or website.

## why would I use this?

There's much better options, which you should probably use instead. This is just a simple python script but that may well be its appeal.

If all you need is basic html/markdown templating then simpblog maybe of use or could maybe be a stop gap solution before you settle on a more feature complete static site generator.

## installation

```
# just script
wget https://github.com/alexk49/simpblog/blob/main/simpblog.py

# or through pip
pip install simpblog
```

If you want the template site files, it will be best to clone the repo:

```
# script with template site:
git clone https://github.com/alexk49/simpblog.git

# set up script manually
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## usage

```
./simpblog.py -h | --help

# pass path of site to build
./simpblog.py -s {site_dir} | --site-dir {site_dir}

# force full rebuild of site
./simpblog.py --force

# run build and start dev server
# if inotifywait is available will watch for changes and reload
./simpblog.py --dev

# specify the port for dev server:
./simpblog.py --dev --port
```

## directory structure

Example files are included in the repo in pages, posts, static and templates for a quick start but these can just be used as a base or ignored completely!


Expected folders are:

pages
posts
templates
static

Pages/posts will accept .md or .html files.

If you have a pages folder then you need a templates/page.html file, if you have a posts folder then you need a templates/post.html file.

You can just have a pages directory or just have a posts directory or have both.

## templates directory

You must have a layout.html file, which will be used to base all over template files on.

## posts/pages directories

In the post directory, you can add front matter to your files like:

```yaml
---
title: Example post
slug: test
date: 2023-09-11
tags: test, example
---
```

Tags are special to posts and if you make a templates/tag.html then html pages will be made containing all the posts that match the tag.

In the pages directory, the only front matter needed is:

```yaml
---
title: About
slug: about
---
```

If use .html files in the pages or post directory then the url slug for a html file will be read from the file name.

## static directory

The static directory is for .css, .js and asset files. These are just copied across to the output folder.

## homepage

The homepage can be made with its own template by placing index.html into the templates directory, or it can use the page.html template by placing index.html or index.md into the pages directory.

## output directory

The built .html files will be generated in a directory called output. It will be built either in the directory that you can the script or in the directory you passed as site_dir.

## dev server

Running the build with the dev server will use python's inbuilt http server to serve the output directory on the localhost. Port 8000 is used by default but this can be changed.

If inotifywait is installed then a rebuild will be triggered when changes are deteced in the pages, posts, static, and templates directories. Otherwise, the server will need to be manually restarted.

On debian/ubuntu, inotifywait can be installed with:

```
sudo apt install inotify-tools
```
