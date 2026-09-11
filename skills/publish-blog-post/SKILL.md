---
name: publish-blog-post
description: >
  Draft, prepare media for, and publish a Quarto blog post using the current
  site's configuration. Use when writing a post, preparing images, uploading
  media, or diagnosing why media does not render on a site.
---

# Publishing a blog post

Use `writing-style` for prose and captions. Run
`waterology config context publish-blog-post` for optional local site guidance.
Read the site's own instructions and configuration before choosing paths,
frontmatter, image sizes, commands, or upload destinations. Do not assume an
existing site, provider, bucket, domain, or installed image utility.

If the CLI is unavailable, use the shared
[local preferences resolver](../project-conventions/references/local-preferences.md)
with this skill name, including common preferences and matching local guidance.

## Prepare the post

1. Use the site's post layout and frontmatter. Supply descriptive image alt text.
2. Follow its media references, including any preview/production URL mapping.
3. Choose available image tools and the site's size and format requirements.
   Check pixel dimensions and aspect ratio after cropping. Confirm social-card
   format support separately from inline images.
4. Run the configured preview and build commands. Inspect the rendered post,
   captions, links, and media at the expected viewing sizes.

## Upload and publish

Use the configured upload command and destination. Supply the correct MIME
type and verify the served response after an authorized upload. Keep credentials
in the provider's credential store or environment, never in site guidance.

Prepare the concrete post and media before requesting publication approval.
Follow existing user authorization. After an authorized deployment, verify the
actual post and media URLs. Record any remaining build or access failures.
