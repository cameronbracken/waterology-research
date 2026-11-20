---
name: publish-blog-post
description: >
  Draft, prepare media for, and publish a Quarto blog post using the current
  site's configuration. Use when writing a blog post, preparing or uploading
  blog media, or diagnosing why media does not render in a blog post.
---

# Publishing a Blog Post

Use [writing-style](../writing-style/SKILL.md) for prose and captions. Inspect the site's own configuration before choosing paths, frontmatter, image dimensions, build commands, or upload targets. Prefer Quarto, WebP for inline media, and [blog defaults](references/blog-defaults.md) when the site leaves choices open.

## Prepare the post

1. Match the site's post directory layout and YAML frontmatter, and supply descriptive alt text on every image.
2. Follow the site's preview/production media URL mapping. Check pixel dimensions, aspect ratio after cropping, and social-card format support separately from inline WebP images.
3. Use [diagrams](../diagrams/SKILL.md) only when creating new conceptual schematics and [figures](../figures/SKILL.md) only when creating new data plots.
4. Run the site's preview/render command and inspect rendered layout, links, and media before proposing publication.

## Upload and publish

Keep bucket/deployment credentials in the environment or provider credential store, never in repository files. Upload with explicit MIME types and deploy only with user authorization, then verify live post and media URLs.
