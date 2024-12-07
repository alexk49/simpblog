# Directories
POSTS := posts
OUTPUT := output
TEMPLATES := $(wildcard templates/*.html)
STATIC := $(wildcard static/*.js static/*.css)

# Find all source Markdown files
SRC_MD := $(wildcard $(POSTS)/*.md)
# Define corresponding HTML output files
DIST_HTML := $(SRC_MD:$(POSTS)/%.md=$(OUTPUT)/%.html)

# Default target: alias for build
all: build

# Build all HTML files
build: $(DIST_HTML)

# Rule to convert Markdown to HTML
$(OUTPUT)/%.html: $(POSTS)/%.md $(TEMPLATES) $(STATIC)
	.venv/bin/python ssg.py

# Clean target: remove all generated HTML files
clean:
	rm -rf $(OUTPUT)

# Development target: run build and start a Python HTTP server
dev: build
	cd $(OUTPUT) && python -m http.server

.PHONY: all build clean dev
