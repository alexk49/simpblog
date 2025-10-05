# ssg

Simple static site generator

## why would I use this?

There's much better options, which you should probably use instead. This is just a simple python script, and that may well be its only appeal.

## installation

```
wget https://github.com/alexk49/ssg/blob/main/ssg.py
```

## usage

```
python ssg.py -h | --help

# pass path of site to build
python ssg.py -s {site_dir} | --site-dir {site_dir}

# force full rebuild of site
python ssg.py --force

# run build and start dev server
# if inotifywait is available will watch for changes and reload
python ssg.py --dev

# specify the port for dev server:
python ssg.py --dev --port
```

## directory structure

Expected folders are:

pages
posts
templates
static

Pages/posts will accept .md or .html files.

If you have a pages folder then you need a templates/page.html file, if you have a posts folder then you need a templates/post.html file.

You can just have a pages dir or just have a posts dir or have both.

## templates dir

You must have a layout.html file, which will be used to base all over template files on.

## posts/pages dirs

In the post dir, you can add front matter to your files like:

```
---
title: Example post
slug: test
date: 2023-09-11
tags: test, example
---
```

Tags are special to posts and if you make a templates/tag.html then html pages will be made containing all the posts that match the tag.

In the pages dir, the only front matter needed is:

---
title: About
slug: about
---

If use .html files in the pages or post dir then the url slug for a html file will be read from the file name.

## static dir

The static dir is for .css, .js and asset files. These are just copied across to the output folder.

## output dir

The built .html files will be generated in a directory called output. It will be built either in the directory that you can the script or in the directory you passed as site_dir.
