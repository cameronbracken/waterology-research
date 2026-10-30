# Blog defaults

Apply these choices when creating a Quarto blog or when the site's existing
configuration leaves them open. Inspect the current configuration first;
these defaults do not assert that a particular site already implements them.

## Posts and media

- Prefer `posts/NNN-slug/index.qmd` for posts and `media/NNN-slug/` for media.
  Follow an established site's numbering and asset layout.
- Include `title`, a concise `description` of roughly 100 characters or less,
  `author`, `date`, `categories`, and a featured `image`. Derive author details
  from site or private configuration rather than hardcoding an identity.
- For sites with distinct local and hosted media, prefer a configured
  `media-base` mapping. Use its shortcode only if the site defines it; otherwise
  use the site's supported relative references. Do not introduce a broken
  shortcode or silently reconfigure deployment while writing a post.
- For side-by-side images, use Quarto's two-column layout with a blank line
  between images. Match their aspect ratios before arranging them, within
  about 0.1% when exact alignment matters. Supply meaningful `fig-alt` text.

## Image preparation

Prefer WebP for inline raster images, quality 82 as a starting point. Aim for
thumbnails under 20 KB and content images near 50 KB where detail permits.
Scientific figure readability takes precedence over a size target. Keep social
and Open Graph card images in JPEG or PNG unless the target preview clients
have been verified to support the alternative.

Prefer installed command line tools for routine media conversion. On macOS,
`sips` can inspect and center-crop a source; `cwebp` can encode it:

```bash
sips -g pixelWidth -g pixelHeight input.png
sips -c 600 900 input.png --out cropped.png
cwebp -q 82 cropped.png -o figure.webp
```

The crop dimensions are an example, not a universal aspect ratio. Preserve the
original image and choose dimensions for the actual layout. Discover equivalent
tools on other platforms; do not require a global image utility just to follow
this recipe.

## Hosted media and publication

Cloudflare R2 is the preferred object store when a blog needs hosted media.
Use an already configured provider when extending a site. Bucket names, account
identifiers, credentials, and upload destinations come from the site or private
configuration; do not provision new services as a side effect of drafting.

For a configured R2 destination, supply MIME type explicitly:

```bash
wrangler r2 object put "$media_bucket/NNN-slug/figure.webp" \
  --file figure.webp --content-type image/webp
curl -sI "$media_url"
```

Set the variables from the approved site configuration. Check that the served
response uses `image/webp` and that the image renders inline. Do not assume the
file extension alone guarantees the served content type.

Use the site's preview and render tasks, such as `pixi run preview` and
`pixi run render` when defined. Check spelling, grammar, media references,
captions, alt text, and the actual rendered layout. Refresh the preview to rule
out stale browser cache. Use a concise imperative or project-standard commit
message when a commit is requested. Follow existing authorization before a push,
upload, or deployment, then inspect the live post and media after publication.
