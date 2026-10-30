---
name: publish-blog-post
description: >
  Draft, prepare media for, and publish a Quarto blog post using the current
  site's configuration. Use when writing a blog post, preparing or uploading
  blog media, or diagnosing why media does not render in a blog post.
---

# Publishing a blog post

Use `writing-style` for prose and captions. Run
`waterology config context publish-blog-post` for optional local site guidance.
Read the site's own instructions and configuration before choosing paths,
frontmatter, image sizes, commands, or upload destinations. Prefer Quarto,
WebP for inline media, and the package's
[blog defaults](references/blog-defaults.md) when the site leaves choices open.
Discover the actual site, bucket, domain, and installed utilities rather than
embedding account details or machine paths in the workflow.

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

Use [diagrams](../diagrams/SKILL.md) only when creating conceptual illustrations,
[data-visualization](../data-visualization/SKILL.md) only for new data figures,
and an available image creation tool for other image work. Reusing existing
media does not require those creation workflows.

## Upload and publish

Use the configured upload command and destination. Supply the correct MIME
type and verify the served response after an authorized upload. Keep credentials
in the provider's credential store or environment, never in site guidance.

Prepare the concrete post and media before requesting publication approval.
Follow existing user authorization. After an authorized deployment, verify the
actual post and media URLs. Record any remaining build or access failures.
