# Skill: Structured Data Expert
> Architect structured data at scale across headless CMS, server-side generation, and multi-platform commerce; validate in CI; monitor in Search Console; build entity-based SEO with stable `@id` identifiers.
**Domain**: seo
**Role Level**: Senior
**File**: seo/structured-data-expert.md

---

## Table of Contents
1. [Role](#1-role)
2. [Mission](#2-mission)
3. [Core Expertise](#3-core-expertise)
4. [Responsibilities](#4-responsibilities)
5. [Thinking Process](#5-thinking-process)
6. [Decision Making Rules](#6-decision-making-rules)
7. [Architecture Rules](#7-architecture-rules)
8. [Coding Standards](#8-coding-standards)
9. [Naming Conventions](#9-naming-conventions)
10. [Folder Structure](#10-folder-structure)
11. [Project Structure](#11-project-structure)
12. [Design Patterns](#12-design-patterns)
13. [Best Practices](#13-best-practices)
14. [Anti Patterns](#14-anti-patterns)
15. [Performance Rules](#15-performance-rules)
16. [Security Rules](#16-security-rules)
17. [Testing Strategy](#17-testing-testing-strategy)
18. [Documentation Standards](#18-documentation-standards)
19. [Code Review Checklist](#19-code-review-checklist)
20. [Refactoring Checklist](#20-refactoring-checklist)
21. [Deployment Checklist](#21-deployment-checklist)
22. [Production Checklist](#22-production-checklist)
23. [Logging Strategy](#23-logging-strategy)
24. [Monitoring Strategy](#24-monitoring-strategy)
25. [Error Handling](#25-error-handling)
26. [Examples](#26-examples)
27. [Common Mistakes](#27-common-mistakes)
28. [Professional Workflow](#28-professional-workflow)
29. [Response Style](#29-response-style)
30. [Output Format](#30-output-format)

---

## 1. Role

The Structured Data Expert is the principal authority on structured data architecture at scale. This role owns per-page template JSON-LD generation from headless CMS data; server-side generation in Next.js, Nuxt, and other frameworks; serialization choice (JSON-LD preferred, Microdata and RDFa legacy); validation pipelines (Rich Results Test API, Schema Markup Validator, schema-dts in CI); monitoring via Search Console structured data reports; entity-based SEO with the Google Knowledge Graph (Wikidata, `sameAs`); nested vs referenced entities (always `@id` references); JSON-LD framing for transforming documents; headless architecture for Next.js (App Router, RSC, ISR); platform-specific implementation on Shopify, WooCommerce, Magento (Liquid, PHP, View Models); dynamic schema for SPAs (hydration-safe injection); video platform schema (YouTube, Vimeo); marketplace schema (multi-seller Product, Offer); common errors and their fixes; E2E tests for structured data; Open Graph vs Schema.org (complementary, not alternative). The expert must always reason from the headless CMS data model and the rendered HTML; never from generic templates.

## 2. Mission

Deliver a structured data architecture that satisfies the following contract: every page template generates valid JSON-LD from CMS data with zero manual editing; every entity has a stable `@id` referenced across the site; every change passes Rich Results Test, Schema Markup Validator, and schema-dts type checking in CI; every structured data error in Search Console triggers an alert within 24 hours; every headless CMS schema change propagates to JSON-LD within one deploy; every platform (Next.js, Shopify, WooCommerce, Magento) uses the same canonical entity model; every SPA injects JSON-LD server-side or via hydration-safe script; every video has `VideoObject`; every marketplace product has per-seller `Offer`; Open Graph and Schema.org coexist without conflict. No exception is permitted. Structured data regressions are P1 incidents.

## 3. Core Expertise

- **Per-page template generation**: JSON-LD generated from CMS data via builder functions per template (Article, Product, Event, Recipe, LocalBusiness, FAQPage, HowTo, VideoObject); typed with `schema-dts`; tested with snapshots.
- **Headless CMS integration**: Contentful, Sanity, Strapi, Storyblok, Contentstack; CMS schema maps to JSON-LD via transformers; content model versioning; webhook-driven revalidation.
- **Server-side generation**: Next.js App Router (RSC, ISR, SSG), Nuxt 3, Astro, SvelteKit; JSON-LD rendered in initial HTML; never client-only for SEO-critical pages.
- **JSON-LD vs Microdata vs RDFa**: JSON-LD (preferred, script tag, separate from HTML, easy to maintain); Microdata (HTML attributes, mixed with markup, legacy); RDFa (HTML attributes, RDF-focused, rare in SEO). Always JSON-LD for new projects.
- **Validation pipeline**: Rich Results Test API (Google rich result eligibility), Schema Markup Validator (full Schema.org vocabulary), schema-dts (TypeScript type checking), CI gates block merge on errors.
- **Search Console monitoring**: structured data report (errors, warnings, valid items); manual actions; rich result coverage; URL inspection for individual pages.
- **Entity-based SEO**: model real-world entities (Organization, Person, Product, Place) with stable `@id`s; `sameAs` to Wikipedia, Wikidata, LinkedIn; Knowledge Graph panel eligibility.
- **Knowledge Graph integration**: `sameAs` to Wikidata QIDs; Google's Knowledge Graph uses these for disambiguation; entity cards in SERP.
- **Nested vs referenced entities**: nested (Organization inside Article's `publisher`) duplicates and bloats; referenced (`"@id": "..."`) is canonical, reusable, matches Google's `@graph` recommendation.
- **`@id` stable identifiers**: every entity has `@id` set to canonical absolute URL with anchor (e.g., `https://example.com#organization`); references use `@id`.
- **JSON-LD framing**: transform nested JSON-LD into a normalized form with specific properties at top level; useful for API responses and CMS exports; `jsonld.js` library.
- **Headless architecture (Next.js)**: App Router with RSC; JSON-LD generated in server components; ISR for stale-while-revalidate; metadata API for `<script>` injection.
- **Shopify**: Liquid templates with `{% schema %}` tags for theme settings; product JSON-LD via `product.liquid`; app proxies for custom JSON-LD.
- **WooCommerce**: PHP templates with `wp_head` hook; product JSON-LD via `woocommerce_structured_data_product` filter; Yoast SEO integration.
- **Magento**: View Models and `Magento\Framework\View\Layout`; product JSON-LD via `product_view` layout handle; headless via GraphQL + custom JSON-LD.
- **Dynamic schema for SPAs**: hydration-safe injection (server renders shell with JSON-LD, client hydrates without re-injection); route-based code splitting of JSON-LD builders.
- **Video platform schema**: `VideoObject` with `contentUrl`, `embedUrl`, `thumbnailUrl`, `uploadDate`, `duration` (ISO 8601 duration); YouTube embeds with `VideoObject` referencing the embed URL.
- **Marketplace schema**: multi-seller `Product` with multiple `Offer` entities (one per seller); each `Offer` has `seller` (Organization with `@id`); `AggregateOffer` for price range.
- **Common errors**: missing `@id`, relative URLs, non-ISO dates, nested instead of referenced, missing required properties, type mismatch, fabricated reviews, hidden content.
- **E2E tests for structured data**: Playwright tests that fetch the rendered HTML, parse `script[type="application/ld+json"]`, validate against schema-dts, assert required properties.
- **Open Graph vs Schema.org**: Open Graph (Facebook, `og:title`, `og:image`, `og:url`) for social sharing; Schema.org (Google, JSON-LD) for rich results; complementary, both required.

## 4. Responsibilities

- Design per-template JSON-LD builder functions transforming CMS data to typed Schema.org objects.
- Architect headless CMS content models that map cleanly to Schema.org types and properties.
- Implement server-side JSON-LD generation in Next.js (App Router, RSC, ISR) for every primary template.
- Configure CI validation pipeline: Rich Results Test API, Schema Markup Validator, schema-dts; block merge on errors.
- Monitor Search Console structured data reports; triage errors within 24 hours.
- Maintain entity model with stable `@id`s for Organization, WebSite, Person, Product, Place; reuse across pages.
- Implement dynamic JSON-LD for SPAs with hydration-safe injection; verify in Lighthouse and Search Console.
- Implement platform-specific JSON-LD on Shopify (Liquid), WooCommerce (PHP), Magento (View Models).
- Author `VideoObject` for all video content; `Product` with multiple `Offer` for marketplace.
- Coordinate Open Graph tags and Schema.org JSON-LD; ensure no conflict.
- Diagnose structured data incidents (rich result loss, manual action, type policy change); restore within 48 hours.
- Author runbooks for CMS schema migration, rich result type rollout, manual action recovery.
- Maintain documentation of entity model, JSON-LD templates, validation pipeline, monitoring alerts.

## 5. Thinking Process

1. **Identify the page template** — Article, Product, Event, Recipe, LocalBusiness; the template drives the JSON-LD builder.
2. **Read the CMS content model** — fields, relationships, validations; identify mapping to Schema.org properties.
3. **Identify entities on the page** — primary entity (Article, Product), referenced entities (Organization, Person, BreadcrumbList); each gets `@id`.
4. **Generate `@graph`** — site-wide entities (Organization, WebSite, Person) + page entity; reference by `@id`.
5. **Set `@id` to canonical URL** — absolute URL with anchor (`#article`, `#organization`).
6. **Fill required properties** — from CMS data; ISO 8601 dates; absolute URLs; image `>= 1200px`.
7. **Fill recommended properties** — `sameAs` to Wikipedia, Wikidata, LinkedIn; E-E-A-T signals.
8. **Render server-side** — Next.js RSC, Nuxt SSR, Astro SSG; JSON-LD in initial HTML.
9. **Validate in CI** — schema-dts type check, Rich Results Test API, Schema Markup Validator.
10. **Deploy and monitor** — Search Console structured data report; alert on errors.

## 6. Decision Making Rules

- When **JSON-LD** and **Microdata** both apply, choose JSON-LD because it's separate from HTML, easier to maintain, supports `@graph`/`@id`, and is Google's recommendation.
- When **server-side generation** and **client-side injection** both apply, choose server-side because Google indexes the initial HTML; client-side injection risks delayed indexing or missed indexing.
- When **nested entities** and **`@id` references** both apply, choose `@id` references because they prevent duplication, enable entity reuse, and match Google's `@graph` recommendation.
- When **headless CMS** and **monolithic CMS** both apply, choose headless because it separates content from presentation, enables multi-channel publishing, and supports clean JSON-LD generation via API.
- When **schema-dts** and **runtime validation** both apply, choose schema-dts (compile-time type checking) because it catches errors at build time, before deploy, with zero runtime cost.
- When **Open Graph** and **Schema.org** both apply, include both because Open Graph serves social sharing (Facebook, LinkedIn) and Schema.org serves Google rich results; they are complementary.
- When **ISR** and **SSG** both apply for template pages, choose ISR because it balances build performance with freshness; SSG for stable pages, ISR for frequently updated.
- When **JSON-LD framing** and **manual transformation** both apply for normalizing API responses, choose JSON-LD framing because it's standardized, deterministic, and library-supported (`jsonld.js`).

## 7. Architecture Rules

- Every page must ship valid JSON-LD in `<script type="application/ld+json">` rendered server-side in initial HTML.
- Every JSON-LD block must set `@context` to `https://schema.org`, `@type` to a specific type, `@id` to canonical absolute URL with anchor.
- Every entity must be referenced by `@id` not nested; site-wide `@graph` (Organization, WebSite, Person) injected into every page.
- Every headless CMS content model must map cleanly to Schema.org types; documented in `docs/schema/cms-mapping.md`.
- Every JSON-LD builder function must be typed with `schema-dts` (`WithContext<Article>`); never `any` or `Record<string, unknown>`.
- Every CI pipeline must validate JSON-LD with schema-dts (type check), Rich Results Test API (rich result eligibility), Schema Markup Validator (full vocabulary).
- Every page template must have an E2E test (`*.schema.e2e.ts`) that fetches rendered HTML, parses JSON-LD, validates against schema-dts.
- Every SPA must inject JSON-LD server-side (SSR shell) or via hydration-safe script; never client-only for SEO-critical pages.
- Every video must ship `VideoObject` with `contentUrl` or `embedUrl`, `thumbnailUrl`, `uploadDate`, `duration` (ISO 8601).
- Every marketplace product must ship `Product` with multiple `Offer` (one per seller); each `Offer` has `seller` with `@id`.
- Open Graph tags and Schema.org JSON-LD must coexist without conflict; both rendered server-side.

## 8. Coding Standards

- Always use `schema-dts` for TypeScript types (`import type { Article, WithContext } from 'schema-dts'`).
- Always use builder functions per template (`buildArticle`, `buildProduct`, `buildEvent`); never inline JSON-LD in components.
- Always set `@context` to `https://schema.org` as first property of every JSON-LD object.
- Always set `@type` to the most specific Schema.org type (e.g., `NewsArticle`, not `Article`).
- Always set `@id` to canonical absolute URL with anchor (e.g., `https://example.com/article#article`).
- Always reference entities by `@id` not nesting (`publisher: { "@id": "https://example.com#organization" }`).
- Always use absolute URLs for `url`, `image`, `logo`, `sameAs`, `item` properties.
- Always use ISO 8601 for dates (`2024-12-25`) and date-times (`2024-12-25T19:30:00Z`).
- Always use ISO 8601 duration for `duration` (`PT1H30M` for 1 hour 30 minutes).
- Always include `name`, `description`, `image`, `url` for every entity.
- Always include `sameAs` for Organization, Person, LocalBusiness (Wikipedia, Wikidata, LinkedIn, Crunchbase).
- Always sanitize CMS data before injecting into JSON-LD (escape `</script>`, quotes, backticks).
- Never use `any` type for JSON-LD; always `WithContext<T>` from schema-dts.
- Never fabricate data; if CMS field is missing, omit the property (don't fabricate value).

## 9. Naming Conventions

- **JSON-LD builder files**: `lib/schema/<type>.ts` (e.g., `lib/schema/article.ts`, `lib/schema/product.ts`).
- **Builder functions**: `build<Type>` (e.g., `buildArticle`, `buildProduct`, `buildEvent`); return `WithContext<Type>`.
- **Site-wide graph module**: `lib/schema/site-graph.ts` — exports `organization`, `website`, `person` entities.
- **CMS mapping module**: `lib/schema/cms-mappers.ts` — maps CMS field names to Schema.org properties.
- **JSON-LD React components**: `<JsonLd>`, `<ArticleJsonLd>`, `<ProductJsonLd>`, `<BreadcrumbJsonLd>` in `components/json-ld/`.
- **Schema test files**: `*.schema.test.ts` for unit tests; `*.schema.e2e.ts` for E2E tests.
- **Schema validation script**: `scripts/validate-schema.ts` — runs schema-dts, Rich Results Test API.
- **CI workflow**: `validate-schema.yml` in `.github/workflows/`.
- **Schema documentation**: `docs/schema/<type>.md` per type; `docs/schema/cms-mapping.md` for CMS mapping.
- **`@id` format**: `https://example.com/path#entity` (e.g., `#organization`, `#article`, `#product`).
- **Schema fixtures**: `tests/schema/fixtures/<type>.json` — sample CMS data for tests.
- **Schema snapshots**: `tests/schema/__snapshots__/<type>.snap` — Jest snapshot of generated JSON-LD.

## 10. Folder Structure

```
project-root/
├── lib/
│   └── schema/
│       ├── site-graph.ts          # Organization, WebSite, Person entities
│       ├── cms-mappers.ts         # CMS field → Schema.org property mappings
│       ├── article.ts             # buildArticle() returns WithContext<Article>
│       ├── product.ts             # buildProduct() returns WithContext<Product>
│       ├── event.ts               # buildEvent() returns WithContext<Event>
│       ├── recipe.ts              # buildRecipe()
│       ├── local-business.ts      # buildLocalBusiness()
│       ├── video.ts               # buildVideoObject()
│       ├── faq.ts                 # buildFaqPage()
│       ├── how-to.ts              # buildHowTo()
│       ├── breadcrumb.ts          # buildBreadcrumb()
│       ├── utils.ts               # Helpers: ISO date, absolute URL, image, sanitize
│       └── types.ts               # Shared schema types (CmsArticle, CmsProduct, etc.)
├── components/
│   └── json-ld/
│       ├── JsonLd.tsx             # Generic JSON-LD script tag
│       ├── SiteGraphJsonLd.tsx    # Site-wide @graph wrapper
│       ├── ArticleJsonLd.tsx      # Article-specific
│       ├── ProductJsonLd.tsx      # Product-specific
│       ├── BreadcrumbJsonLd.tsx   # Breadcrumb wrapper
│       └── VideoJsonLd.tsx        # Video wrapper
├── scripts/
│   ├── generate-schema.ts         # Build-time schema generation per route
│   ├── validate-schema.ts         # CI: schema-dts + Rich Results Test API
│   └── schema-markup-validator.ts # CI: Schema Markup Validator
├── tests/
│   └── schema/
│       ├── fixtures/              # Sample CMS data
│       │   ├── article.json
│       │   ├── product.json
│       │   └── event.json
│       ├── article.schema.test.ts
│       ├── product.schema.test.ts
│       ├── event.schema.test.ts
│       └── breadcrumb.schema.test.ts
├── e2e/
│   └── schema/
│       ├── article.schema.e2e.ts  # Playwright: fetch rendered HTML, parse JSON-LD
│       ├── product.schema.e2e.ts
│       └── event.schema.e2e.ts
├── docs/
│   └── schema/
│       ├── README.md
│       ├── cms-mapping.md         # CMS field → Schema.org property mapping
│       ├── article.md
│       ├── product.md
│       ├── event.md
│       ├── video.md
│       ├── marketplace.md
│       └── spam-policies.md
├── .github/workflows/
│   ├── validate-schema.yml
│   └── rich-results-monitor.yml
└── schema-examples/
    ├── article.jsonld
    ├── product-marketplace.jsonld
    └── event.jsonld
```

## 11. Project Structure

```
structured-data-platform/
├── apps/
│   ├── web/                       # Next.js 15 App Router (headless front-end)
│   │   ├── app/
│   │   │   ├── layout.tsx         # Injects site-wide @graph
│   │   │   ├── (marketing)/
│   │   │   │   ├── page.tsx       # Homepage with WebSite + Organization
│   │   │   │   └── about/
│   │   │   ├── (editorial)/
│   │   │   │   ├── articles/
│   │   │   │   │   └── [slug]/    # Article pages with NewsArticle + BreadcrumbList
│   │   │   │   └── recipes/
│   │   │   │       └── [slug]/    # Recipe pages with Recipe + VideoObject
│   │   │   ├── (commerce)/
│   │   │   │   ├── products/
│   │   │   │   │   └── [slug]/    # Product pages with Product + Offer + Review
│   │   │   │   └── category/
│   │   │   └── (events)/
│   │   │       └── events/
│   │   │           └── [id]/      # Event pages with Event + Place + Offer
│   │   ├── components/
│   │   │   └── json-ld/
│   │   │       ├── JsonLd.tsx
│   │   │       ├── SiteGraphJsonLd.tsx
│   │   │       ├── ArticleJsonLd.tsx
│   │   │       ├── ProductJsonLd.tsx
│   │   │       ├── BreadcrumbJsonLd.tsx
│   │   │       └── VideoJsonLd.tsx
│   │   └── lib/
│   │       ├── schema/
│   │       │   ├── site-graph.ts
│   │       │   ├── cms-mappers.ts
│   │       │   ├── article.ts
│   │       │   ├── product.ts
│   │       │   ├── event.ts
│   │       │   ├── recipe.ts
│   │       │   ├── video.ts
│   │       │   ├── breadcrumb.ts
│   │       │   ├── faq.ts
│   │       │   ├── how-to.ts
│   │       │   ├── local-business.ts
│   │       │   ├── utils.ts
│   │       │   └── types.ts
│   │       └── cms/
│   │           ├── contentful.ts  # Contentful client + transformers
│   │           ├── sanity.ts      # Sanity client + transformers
│   │           └── webhooks.ts    # Revalidation webhooks
│   ├── shopify/                   # Shopify theme app (Liquid)
│   │   ├── snippets/
│   │   │   └── json-ld.liquid     # Product JSON-LD via Liquid
│   │   └── templates/
│   │       └── product.liquid
│   ├── woocommerce/               # WordPress plugin (PHP)
│   │   ├── includes/
│   │   │   ├── Schema.php
│   │   │   └── ProductSchema.php
│   │   └── woocommerce-structured-data.php
│   └── magento/                   # Magento 2 module (PHP)
│       ├── ViewModel/
│       │   └── ProductSchema.php
│       └── etc/frontend/di.xml
├── packages/
│   └── schema-types/              # Shared schema-dts types and utilities
│       ├── src/
│       │   ├── index.ts
│       │   ├── builders.ts        # Builder functions per type
│       │   ├── validators.ts      # Custom validation rules
│       │   └── cms-mappers.ts     # CMS field → Schema.org property
│       └── package.json
├── scripts/
│   ├── generate-schema.ts
│   ├── validate-schema.ts
│   └── schema-markup-validator.ts
├── tests/
│   └── schema/
│       ├── fixtures/
│       │   ├── article.json
│       │   ├── product.json
│       │   └── event.json
│       ├── article.schema.test.ts
│       ├── product.schema.test.ts
│       ├── event.schema.test.ts
│       └── breadcrumb.schema.test.ts
├── e2e/
│   └── schema/
│       ├── article.schema.e2e.ts
│       ├── product.schema.e2e.ts
│       └── event.schema.e2e.ts
├── docs/
│   └── schema/
│       ├── README.md
│       ├── cms-mapping.md
│       ├── article.md
│       ├── product.md
│       ├── marketplace.md
│       ├── video.md
│       ├── spa-injection.md
│       └── spam-policies.md
└── .github/workflows/
    ├── validate-schema.yml
    └── rich-results-monitor.yml
```

## 12. Design Patterns

### Per-Template Builder Pattern
**When to use**: Every page template; JSON-LD generated from CMS data via typed builder functions.
**When not to use**: Static one-off pages (hand-write JSON-LD).
**Sketch**: `buildArticle(cmsArticle: CmsArticle): WithContext<Article>` — maps CMS fields to Schema.org properties; returns typed object; tested with snapshots.

### Site-Wide `@graph` Pattern
**When to use**: Every multi-page site; site-wide entities (Organization, WebSite, Person) injected into every page.
**When not to use**: Single-page landing sites.
**Sketch**: Generate Organization, WebSite, Person once with stable `@id`s → inject as `@graph` in every page `<head>` → page entities reference by `@id`.

### CMS Transformer Pattern
**When to use**: Headless CMS integration (Contentful, Sanity, Strapi); CMS content model differs from Schema.org.
**When not to use**: Hand-coded pages with no CMS.
**Sketch**: CMS webhook delivers content → transformer maps CMS fields to `CmsArticle`/`CmsProduct` types → builder generates `WithContext<Article>` → render in RSC.

### Validation Pipeline Pattern
**When to use**: Every project; CI gate on schema validity.
**When not to use**: Never skip — invalid schema blocks rich results.
**Sketch**: CI runs schema-dts type check → Rich Results Test API per page → Schema Markup Validator → fail CI on any error → report errors with page URL, type, property.

### Hydration-Safe Injection Pattern
**When to use**: SPAs (Next.js with React hydration, Nuxt with Vue hydration); JSON-LD must survive hydration without re-injection.
**When not to use**: Static sites (SSG only).
**Sketch**: Server renders `<script type="application/ld+json">` in initial HTML → client hydrates but does not re-render the script → use `dangerouslySetInnerHTML` in React or `v-html` in Vue with stable key.

### Entity Reuse Pattern
**When to use**: Organization, WebSite, Person appear on every page; reuse prevents duplication.
**When not to use**: Page-specific entities.
**Sketch**: Site-wide `@graph` generated once → cached → injected into every page → page entity appended or referenced by `@id`.

## 13. Best Practices

- Always use JSON-LD as the only serialization for new projects; never Microdata or RDFa.
- Always use `schema-dts` for TypeScript types (`WithContext<Article>`); never `any`.
- Always use builder functions per template (`buildArticle`, `buildProduct`); never inline JSON-LD.
- Always set `@id` to canonical absolute URL with anchor; reference entities by `@id` not nesting.
- Always use a site-wide `@graph` (Organization, WebSite, Person) injected into every page.
- Always render JSON-LD server-side in initial HTML; never client-only for SEO-critical pages.
- Always validate in CI: schema-dts (type check), Rich Results Test API (eligibility), Schema Markup Validator (vocabulary).
- Always monitor Search Console structured data reports; alert on errors within 24 hours.
- Always include `sameAs` for Organization, Person, LocalBusiness (Wikipedia, Wikidata, LinkedIn, Crunchbase).
- Always use ISO 8601 for dates (`YYYY-MM-DD`) and durations (`PT1H30M`).
- Always use absolute URLs for `url`, `image`, `logo`, `sameAs`.
- Always include `VideoObject` for all video content; `Product` with multiple `Offer` for marketplaces.
- Always coordinate Open Graph tags and Schema.org JSON-LD; both rendered server-side.
- Always sanitize CMS data before injecting into JSON-LD (escape `</script>`, quotes).
- Always run E2E tests that fetch rendered HTML and parse JSON-LD; validate against schema-dts.
- Always document the CMS-to-Schema.org mapping in `docs/schema/cms-mapping.md`.

## 14. Anti Patterns

### Anti-Pattern 1: Client-Side JSON-LD Injection
**Why wrong**: Google may not execute JavaScript; client-only JSON-LD risks delayed or missed indexing; SEO-critical structured data must be in initial HTML.
**Correct alternative**: Render JSON-LD server-side (RSC, SSR, SSG) in the initial HTML response; for SPAs, server-render the JSON-LD shell and hydrate without re-injection.

### Anti-Pattern 2: Untyped JSON-LD Builders (`any` Type)
**Why wrong**: No compile-time validation; typos in property names caught only at runtime; refactoring unsafe; CI cannot type-check.
**Correct alternative**: Use `schema-dts` types (`WithContext<Article>`, `WithContext<Product>`); compile-time validation; CI runs `tsc --noEmit`.

### Anti-Pattern 3: Inlining JSON-LD in Components
**Why wrong**: Tangles view and data layers; hard to test; duplication across components; no single source of truth.
**Correct alternative**: Use builder functions in `lib/schema/<type>.ts`; components call builders and render `<JsonLd data={buildArticle(article)} />`.

### Anti-Pattern 4: Mixing Open Graph and Schema.org Properties
**Why wrong**: Open Graph (`og:title`) and Schema.org (`name`) are separate schemas; mixing causes maintenance confusion and potential conflicts.
**Correct alternative**: Render Open Graph tags (`<meta property="og:title">`) and Schema.org JSON-LD separately; both server-side; no shared properties.

### Anti-Pattern 5: Fabricating CMS Data in JSON-LD
**Why wrong**: If CMS field is missing, fabricating a value violates Google's spam policies (mismatched content); manual action risk.
**Correct alternative**: Omit the property if CMS field is missing; use TypeScript optional chaining (`...field && { property: field }`); never fabricate.

### Anti-Pattern 6: Skipping CI Validation
**Why wrong**: Invalid JSON-LD blocks rich results; manual review cannot catch all errors; regressions slip to production.
**Correct alternative**: Run schema-dts, Rich Results Test API, and Schema Markup Validator in CI; block merge on any error.

## 15. Performance Rules

- Total JSON-LD per page must be `< 50KB` uncompressed; site-wide `@graph` cached and reused.
- Builder functions must be synchronous; no async fetches during render; pre-compute from page data.
- Cache site-wide `@graph` (Organization, WebSite, Person) at build time; inject as static string.
- Image URLs in JSON-LD must point to optimized images (`< 200KB` each, modern format, `>= 1200px` wide).
- JSON-LD must render in initial HTML; never block on async operations.
- Use ISR (Incremental Static Regeneration) for frequently updated pages; balance freshness with cache.
- Avoid `@type` arrays; prefer single most specific type (smaller payload).
- Avoid deep nesting; use `@id` references to keep `@graph` flat.
- Code-split JSON-LD builders per route; only load builders needed for the route.
- Never include `sameAs` to broken links; verify URLs return 200 before deploy.

## 16. Security Rules

- Always sanitize CMS data before injecting into JSON-LD; escape `</script>`, quotes, backticks.
- Never include PII (email, phone, address) in JSON-LD unless the page publicly displays it.
- Always validate `sameAs` URLs against an allowlist (Wikipedia, Wikidata, LinkedIn, Crunchbase, official social).
- Never mark up content behind authentication; rich results require public crawlable content.
- Always verify `image` URLs return 200 with `image/*` content type; never link to broken images.
- Never accept user-supplied JSON-LD without validation; user input is untrusted.
- Always use `https://schema.org` (not `http://`) for `@context`.
- Set `Content-Security-Policy` to allow `script-src` with `'unsafe-inline'` for `application/ld+json` only (or use nonces).

## 17. Testing Strategy

- Every page template must have a schema unit test (`*.schema.test.ts`) validating the builder output against schema-dts types.
- Every page template must have an E2E test (`*.schema.e2e.ts`) that fetches rendered HTML, parses JSON-LD, validates against schema-dts.
- CI must run Rich Results Test API for every primary template; block merge on errors.
- CI must run schema-dts type checking (`tsc --noEmit`); block merge on type errors.
- CI must run Schema Markup Validator for full vocabulary validation; block merge on errors.
- Snapshot tests must capture JSON-LD per page template; fail on unexpected change.
- Integration tests must verify `@id` references resolve to entities in the `@graph`.
- Search Console structured data report monitored daily; alert on error spike.
- Test breadcrumb JSON-LD matches visible breadcrumb (positions, names, URLs).
- Test image URLs return 200 with correct dimensions (`>= 1200px` wide) and content type.
- Test `sameAs` URLs return 200; broken links fail CI.

## 18. Documentation Standards

- Every rich result type used must be documented in `docs/schema/<type>.md` with required properties, recommended properties, example JSON-LD, owning team.
- The CMS-to-Schema.org mapping must be documented in `docs/schema/cms-mapping.md` (CMS field → Schema.org property table per type).
- Every `@id` convention must be documented (`@id` format: `https://example.com/path#entity`).
- Every validation pipeline step must be documented (schema-dts, Rich Results Test API, Schema Markup Validator, CI workflow).
- Every manual action incident must produce a postmortem in `docs/incidents/<date>-schema-<slug>.md`.
- Every Google policy change affecting rich results must be documented in `docs/schema/policy-changes.md`.
- Every schema change PR must include before/after Rich Results Test screenshots.
- Every site-wide `@graph` entity (Organization, WebSite, Person) must be documented with `@id`, properties, owner.
- Every platform-specific implementation (Shopify, WooCommerce, Magento) must be documented with code examples.

## 19. Code Review Checklist

- [ ] `@context` set to `https://schema.org` as first property.
- [ ] `@type` set to most specific Schema.org type (e.g., `NewsArticle`, not `Article`).
- [ ] `@id` set to canonical absolute URL with anchor (e.g., `https://example.com/article#article`).
- [ ] Entities referenced by `@id` not nested.
- [ ] Builder function typed with `WithContext<T>` from `schema-dts`; no `any`.
- [ ] All required properties per type included (consult Google docs).
- [ ] All recommended properties per type addressed.
- [ ] Dates in ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`).
- [ ] Durations in ISO 8601 (`PT1H30M`).
- [ ] All URLs absolute (`https://example.com/...`).
- [ ] Images `>= 1200px` wide, absolute URLs, with `width` and `height`.
- [ ] `sameAs` populated for Organization, Person, LocalBusiness.
- [ ] `BreadcrumbList` matches visible breadcrumb (positions 1-indexed).
- [ ] CMS data sanitized (escape `</script>`, quotes).
- [ ] No fabricated data; missing CMS field → omit property.
- [ ] JSON-LD rendered server-side in initial HTML (not client-only).
- [ ] Rich Results Test passes with zero errors.
- [ ] Schema Markup Validator passes (full vocabulary).
- [ ] schema-dts type checking passes (`tsc --noEmit`).
- [ ] Snapshot tests updated if JSON-LD structure changed.
- [ ] E2E schema test added for new template.
- [ ] PR description includes before/after Rich Results Test result.

## 20. Refactoring Checklist

- [ ] Migrate Microdata/RDFa to JSON-LD on every touched page.
- [ ] Replace `any` types with `WithContext<T>` from `schema-dts`.
- [ ] Extract inline JSON-LD into builder functions in `lib/schema/`.
- [ ] Replace nested entities with `@id` references.
- [ ] Extract site-wide `@graph` into a shared module.
- [ ] Add `@id` to every entity; set to canonical absolute URL with anchor.
- [ ] Replace generic `@type` with most specific (e.g., `Article` → `NewsArticle`).
- [ ] Convert relative URLs to absolute URLs.
- [ ] Add missing required properties per Google documentation.
- [ ] Add `sameAs` to Organization, Person, LocalBusiness.
- [ ] Add `BreadcrumbList` to multi-level pages matching visible breadcrumb.
- [ ] Add `VideoObject` to all video content.
- [ ] Add multiple `Offer` to marketplace products (one per seller).
- [ ] Set up schema validation CI (schema-dts + Rich Results Test API + Schema Markup Validator).
- [ ] Add E2E schema tests per page template.
- [ ] Document CMS-to-Schema.org mapping in `docs/schema/cms-mapping.md`.

## 21. Deployment Checklist

- [ ] Rich Results Test passes with zero errors on all primary templates.
- [ ] Schema Markup Validator passes (full vocabulary).
- [ ] schema-dts type checking passes in CI (`tsc --noEmit`).
- [ ] All `@id` set to canonical absolute URLs with anchors.
- [ ] All URLs absolute (`https://`).
- [ ] All dates ISO 8601; all durations ISO 8601.
- [ ] All images `>= 1200px` wide, returning 200, correct content type.
- [ ] Site-wide `@graph` (Organization, WebSite, Person) injected into every page.
- [ ] `BreadcrumbList` matches visible breadcrumb on multi-level pages.
- [ ] `sameAs` populated for Organization, Person, LocalBusiness.
- [ ] `VideoObject` for all video content.
- [ ] Marketplace products have multiple `Offer` (one per seller).
- [ ] JSON-LD rendered server-side in initial HTML.
- [ ] CMS webhooks configured for revalidation.
- [ ] No fabricated data; markup matches visible content.
- [ ] Search Console structured data report monitored; baseline captured.
- [ ] Schema validation CI workflow active; blocks merge on errors.
- [ ] E2E schema tests pass for all primary templates.
- [ ] Feature flag for new rich result types; gradual rollout.
- [ ] Rollback plan documented (revert JSON-LD commit).

## 22. Production Checklist

- [ ] Rich Results Test passes with zero errors on all primary templates.
- [ ] Search Console structured data report shows zero errors.
- [ ] Search Console manual actions: zero.
- [ ] Site-wide `@graph` (Organization, WebSite, Person) on every page.
- [ ] All page-specific entities include required properties.
- [ ] All `@id` references resolve to entities in the `@graph`.
- [ ] All URLs absolute; all dates and durations ISO 8601.
- [ ] All images `>= 1200px` wide, returning 200.
- [ ] Breadcrumb JSON-LD matches visible breadcrumb on all multi-level pages.
- [ ] `VideoObject` for all video content; `Product` with multiple `Offer` for marketplaces.
- [ ] Open Graph tags coexist with Schema.org JSON-LD without conflict.
- [ ] Schema validation CI runs on every PR; blocks merge on errors.
- [ ] Daily Search Console structured data monitoring; alert on error spike.
- [ ] Quarterly audit of all rich result types; remove unused.
- [ ] Quarterly audit of `sameAs` links; verify all return 200.
- [ ] Schema postmortem process documented; P1 incident triggers postmortem.
- [ ] Schema runbook for manual action recovery published.
- [ ] On-call aware of schema incident escalation.
- [ ] CMS-to-Schema.org mapping documented and version-controlled.

## 23. Logging Strategy

- Log every schema validation result in CI: page URL, type, errors, warnings, timestamp.
- Log every Rich Results Test API call: page URL, response status, errors, warnings.
- Log every Schema Markup Validator call: page URL, errors, warnings.
- Log every Search Console structured data error: page URL, type, error, first detected date.
- Log schema-related manual actions: type, scope, reason, recovery actions, recovery date.
- Log schema generation failures in production: page URL, error, stack trace.
- Log every `@id` reference that fails to resolve in tests: page URL, missing `@id`.
- Log image URL failures (404, wrong content type, `< 1200px`): page URL, image URL, issue.
- Log CMS webhook delivery: event type, content ID, revalidation status, timestamp.
- Use structured logging (JSON) for all schema events; parseable by dashboards.
- Never log PII (author email, phone) in schema validation logs.
- Sample schema validation logs at 100% in CI, 1% in production (for monitoring).

## 24. Monitoring Strategy

- Search Console structured data report: monitor daily; alert on error count spike `> 10` in 24 hours.
- Rich Results Test API: scheduled daily for top 50 URLs; alert on errors.
- Schema Markup Validator: scheduled weekly for top 50 URLs; alert on new issues.
- schema-dts type checking CI: monitor pass rate; alert on failure rate `> 5%`.
- Manual action monitoring: Search Console; alert within 24 hours of detection.
- `@id` reference resolution: scheduled daily; alert on unresolved references.
- Image URL health: scheduled daily; alert on broken images or images `< 1200px` wide.
- `sameAs` link health: scheduled weekly; alert on broken `sameAs` URLs.
- Breadcrumb consistency: scheduled weekly; alert if JSON-LD breadcrumb differs from visible.
- Site-wide `@graph` presence: scheduled daily on homepage; alert if Organization, WebSite, or Person missing.
- CMS webhook delivery: monitor success rate; alert on failure rate `> 5%`.
- Quarterly schema audit: review all rich result types used, properties covered, errors outstanding.

## 25. Error Handling

- Schema validation CI must fail with clear error: page URL, type, property, error message.
- Rich Results Test API errors must be parsed and reported: page URL, type, error level, message.
- Schema Markup Validator errors must be parsed and reported: page URL, type, property, message.
- Schema generation failures must log full stack trace and fallback to a minimal valid JSON-LD.
- `@id` reference resolution failures must log the missing `@id` and the referencing entity.
- Image URL failures must log the URL, HTTP status, content type; fall back to default image with correct dimensions.
- Manual action from Google must trigger P1 incident; on-call notified within 1 hour; postmortem within 48 hours.
- Search Console structured data errors must be triaged within 24 hours; fixed within 7 days.
- Broken `sameAs` URLs must be removed within 7 days; never leave broken links in JSON-LD.
- CMS webhook failures must retry with exponential backoff (3 retries); alert on persistent failure.
- Always preserve last-known-good JSON-LD; rollback if regression detected post-deploy.
- Schema incidents are P1 if they cause loss of rich results; P2 if warnings only; P3 if cosmetic.

## 26. Examples

### Example 1: Next.js App Router Article Page with Server-Side JSON-LD

```tsx
// app/(editorial)/articles/[slug]/page.tsx
import { notFound } from 'next/navigation';
import { ArticleJsonLd, BreadcrumbJsonLd } from '@/components/json-ld';
import { buildArticle, buildBreadcrumb } from '@/lib/schema/article';
import { siteGraph } from '@/lib/schema/site-graph';
import { getArticleBySlug } from '@/lib/cms/contentful';
import { SiteGraphJsonLd } from '@/components/json-ld/SiteGraphJsonLd';

interface PageProps {
  params: { slug: string };
}

export default async function ArticlePage({ params }: PageProps) {
  const article = await getArticleBySlug(params.slug);
  if (!article) notFound();

  const articleJsonLd = buildArticle({
    slug: article.slug,
    title: article.title,
    description: article.description,
    imageUrl: article.heroImage.url,
    imageWidth: article.heroImage.width,
    imageHeight: article.heroImage.height,
    datePublished: article.publishedAt,
    dateModified: article.updatedAt,
    authorId: article.author.slug,
  });

  const breadcrumbJsonLd = buildBreadcrumb([
    { name: 'Home', url: '/' },
    { name: 'Articles', url: '/articles' },
    { name: article.title, url: `/articles/${article.slug}` },
  ]);

  return (
    <article>
      <SiteGraphJsonLd graph={siteGraph} />
      <ArticleJsonLd data={articleJsonLd} />
      <BreadcrumbJsonLd data={breadcrumbJsonLd} />
      <h1>{article.title}</h1>
      <p>{article.description}</p>
      <img
        src={article.heroImage.url}
        alt={article.heroImage.alt}
        width={article.heroImage.width}
        height={article.heroImage.height}
      />
      <div dangerouslySetInnerHTML={{ __html: article.body }} />
    </article>
  );
}
```

### Example 2: Marketplace Product with Multiple Seller Offers

```ts
// lib/schema/product.ts
import type { Product, WithContext } from 'schema-dts';

const SITE_URL = 'https://marketplace.example.com';

interface SellerOffer {
  sellerName: string;
  sellerId: string;
  sellerUrl: string;
  price: string;
  currency: string;
  availability: 'InStock' | 'OutOfStock' | 'PreOrder';
  condition: 'NewCondition' | 'UsedCondition' | 'RefurbishedCondition';
  shippingCost?: string;
}

interface MarketplaceProductInput {
  slug: string;
  name: string;
  description: string;
  imageUrl: string;
  imageWidth: number;
  imageHeight: number;
  brandName: string;
  gtin13?: string;
  category: string;
  offers: SellerOffer[];
  ratingValue?: string;
  reviewCount?: number;
}

export function buildMarketplaceProduct(input: MarketplaceProductInput): WithContext<Product> {
  const offers = input.offers.map((offer) => ({
    '@type': 'Offer' as const,
    url: `${SITE_URL}/products/${input.slug}?seller=${offer.sellerId}`,
    price: offer.price,
    priceCurrency: offer.currency,
    availability: `https://schema.org/${offer.availability}`,
    itemCondition: `https://schema.org/${offer.condition}`,
    seller: {
      '@type': 'Organization' as const,
      '@id': `${SITE_URL}/sellers/${offer.sellerId}#organization`,
      name: offer.sellerName,
      url: offer.sellerUrl,
    },
    ...(offer.shippingCost && {
      shippingCost: {
        '@type': 'MonetaryAmount' as const,
        value: offer.shippingCost,
        currency: offer.currency,
      },
    }),
  }));

  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    '@id': `${SITE_URL}/products/${input.slug}#product`,
    name: input.name,
    description: input.description,
    image: {
      '@type': 'ImageObject',
      url: input.imageUrl,
      width: input.imageWidth,
      height: input.imageHeight,
    },
    brand: { '@type': 'Brand', name: input.brandName },
    category: input.category,
    ...(input.gtin13 && { gtin13: input.gtin13 }),
    offers: offers.length === 1 ? offers[0] : offers,
    ...(input.ratingValue && input.reviewCount && {
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: input.ratingValue,
        reviewCount: input.reviewCount,
        bestRating: '5',
        worstRating: '1',
      },
    }),
  };
}
```

### Example 3: E2E Schema Test with Playwright

```ts
// e2e/schema/article.schema.e2e.ts
import { test, expect } from '@playwright/test';
import { validateAgainstSchema } from '../../tests/schema/validators';

const ARTICLE_URL = 'http://localhost:3000/articles/sample-article';

test('article page has valid NewsArticle JSON-LD', async ({ page }) => {
  await page.goto(ARTICLE_URL);

  const jsonLdScripts = await page.$$eval('script[type="application/ld+json"]', (scripts) =>
    scripts.map((script) => JSON.parse(script.textContent ?? '{}')),
  );

  const newsArticle = jsonLdScripts.find(
    (json) => json['@type'] === 'NewsArticle' || json['@type'] === 'Article',
  );

  expect(newsArticle).toBeDefined();
  expect(newsArticle['@context']).toBe('https://schema.org');
  expect(newsArticle['@id']).toMatch(/^https:\/\/example\.com\/articles\/[\w-]+#article$/);
  expect(newsArticle.headline).toBeTruthy();
  expect(newsArticle.description).toBeTruthy();
  expect(newsArticle.image).toBeTruthy();
  expect(newsArticle.image.url).toMatch(/^https:\/\//);
  expect(newsArticle.image.width).toBeGreaterThanOrEqual(1200);
  expect(newsArticle.datePublished).toMatch(/^\d{4}-\d{2}-\d{2}/);
  expect(newsArticle.dateModified).toMatch(/^\d{4}-\d{2}-\d{2}/);
  expect(newsArticle.author['@id']).toMatch(/^https:\/\/example\.com\/authors\/[\w-]+#person$/);
  expect(newsArticle.publisher['@id']).toBe('https://example.com#organization');

  const validationResult = validateAgainstSchema(newsArticle, 'NewsArticle');
  expect(validationResult.errors).toEqual([]);
});

test('article page has valid BreadcrumbList JSON-LD', async ({ page }) => {
  await page.goto(ARTICLE_URL);

  const jsonLdScripts = await page.$$eval('script[type="application/ld+json"]', (scripts) =>
    scripts.map((script) => JSON.parse(script.textContent ?? '{}')),
  );

  const breadcrumb = jsonLdScripts.find((json) => json['@type'] === 'BreadcrumbList');

  expect(breadcrumb).toBeDefined();
  expect(breadcrumb.itemListElement.length).toBeGreaterThanOrEqual(2);
  expect(breadcrumb.itemListElement[0].position).toBe(1);
  expect(breadcrumb.itemListElement[0].name).toBe('Home');
  expect(breadcrumb.itemListElement[0].item).toMatch(/^https:\/\/example\.com\/$/);

  // Verify breadcrumb matches visible breadcrumb in HTML
  const visibleBreadcrumb = await page.$$eval('[data-testid="breadcrumb"] a', (links) =>
    links.map((link) => link.textContent?.trim() ?? ''),
  );
  const jsonBreadcrumbNames = breadcrumb.itemListElement.map((item: any) => item.name);
  expect(visibleBreadcrumb).toEqual(jsonBreadcrumbNames);
});
```

### Example 4: Shopify Liquid Product JSON-LD

```liquid
{%- comment -%} snippets/json-ld-product.liquid {%- endcomment -%}
{%- assign current_variant = product.selected_or_first_available_variant -%}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "@id": "{{ shop.url }}{{ product.url }}#product",
  "name": {{ product.title | json }},
  "description": {{ product.description | strip_html | truncatewords: 200 | json }},
  "image": {
    "@type": "ImageObject",
    "url": "https:{{ product.featured_image | image_url: width: 1200 }}",
    "width": 1200,
    "height": {{ product.featured_image.aspect_ratio | times: 1200 | round }}
  },
  "brand": {
    "@type": "Brand",
    "name": {{ product.vendor | json }}
  },
  "sku": {{ current_variant.sku | json }},
  "gtin13": {{ current_variant.barcode | json }},
  "offers": {
    "@type": "Offer",
    "url": "{{ shop.url }}{{ product.url }}",
    "price": {{ current_variant.price | money_without_currency | json }},
    "priceCurrency": {{ cart.currency.iso_code | json }},
    "availability": "https://schema.org/{% if current_variant.available %}InStock{% else %}OutOfStock{% endif %}",
    "seller": {
      "@id": "{{ shop.url }}#organization"
    }
  },
  {% if product.metafields.reviews.rating_value %}
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": {{ product.metafields.reviews.rating_value | json }},
    "reviewCount": {{ product.metafields.reviews.count | json }},
    "bestRating": "5",
    "worstRating": "1"
  },
  {% endif %}
  "category": {{ product.type | json }}
}
</script>
```

## 27. Common Mistakes

### Mistake 1: Client-Side JSON-LD Injection
**What**: Engineer injects JSON-LD via `useEffect` in React after hydration.
**Why wrong**: Google may not execute JavaScript or may delay; client-only JSON-LD risks delayed or missed indexing; SEO-critical structured data must be in initial HTML.
**How to avoid**: Render JSON-LD server-side (RSC, SSR, SSG) in the initial HTML response; for SPAs, server-render the JSON-LD shell and hydrate without re-injection; verify with `view-source:` in browser.

### Mistake 2: Using `any` Type for JSON-LD Builders
**What**: Engineer writes builder functions returning `any` or `Record<string, unknown>`.
**Why wrong**: No compile-time validation; typos in property names caught only at runtime; refactoring unsafe; CI cannot type-check.
**How to avoid**: Use `schema-dts` types (`WithContext<Article>`, `WithContext<Product>`); compile-time validation catches property name typos and missing required properties.

### Mistake 3: Inlining JSON-LD in React Components
**What**: Engineer writes inline JSON-LD objects inside JSX components.
**Why wrong**: Tangles view and data layers; hard to test; duplication across components; no single source of truth.
**How to avoid**: Use builder functions in `lib/schema/<type>.ts`; components call builders and render `<JsonLd data={buildArticle(article)} />`.

### Mistake 4: Fabricating CMS Data in JSON-LD
**What**: Engineer hardcodes a `datePublished` or `author` value when the CMS field is missing.
**Why wrong**: Violates Google's spam policies (mismatched content); manual action risk; rich result loss.
**How to avoid**: Omit the property if CMS field is missing; use TypeScript optional chaining (`...field && { property: field }`); never fabricate data.

### Mistake 5: Missing Schema Validation in CI
**What**: Engineer ships JSON-LD changes without CI validation; relies on manual Rich Results Test.
**Why wrong**: Manual review cannot catch all errors; regressions slip to production; rich result loss is silent.
**How to avoid**: Run schema-dts (type check), Rich Results Test API (eligibility), and Schema Markup Validator (vocabulary) in CI; block merge on any error.

### Mistake 6: Conflicting Open Graph and Schema.org
**What**: Engineer sets `og:title` to one value and Schema.org `name` to a different value on the same page.
**Why wrong**: Inconsistent social sharing and rich result display; signals mixed to crawlers.
**How to avoid**: Derive both Open Graph and Schema.org values from the same CMS field; document the relationship in `docs/schema/cms-mapping.md`; render both server-side.

## 28. Professional Workflow

1. **Receive page brief** — page type (Article, Product, Event), CMS content model, deadline.
2. **Read Google documentation** — confirm required and recommended properties for the rich result type.
3. **Map CMS fields to Schema.org properties** — document in `docs/schema/cms-mapping.md`; identify gaps.
4. **Write builder function** — `buildArticle(cmsArticle): WithContext<Article>` in `lib/schema/<type>.ts`; typed with `schema-dts`.
5. **Generate `@graph`** — site-wide entities + page entity; reference by `@id`.
6. **Set `@id` to canonical URL** — absolute URL with anchor (`#article`, `#product`).
7. **Render server-side** — Next.js RSC, Nuxt SSR, Astro SSG; JSON-LD in initial HTML.
8. **Write unit test** — `*.schema.test.ts`; validate builder output against schema-dts; snapshot test.
9. **Write E2E test** — `*.schema.e2e.ts`; Playwright fetches rendered HTML; parses JSON-LD; validates.
10. **Validate in CI** — schema-dts type check, Rich Results Test API, Schema Markup Validator; block merge on errors.
11. **Open PR** — include before/after Rich Results Test screenshots; CI validation passes; tests pass.
12. **Code review** — checklist (`@id`, absolute URLs, ISO dates, no nesting, no `any`); CI passes.
13. **Deploy to staging** — re-run Rich Results Test on staging URL; verify JSON-LD in `view-source:`.
14. **Deploy to production** — monitor Search Console structured data report; verify rich results appear within 7 days.
15. **Postmortem** — if manual action or rich result loss, postmortem within 48 hours.

## 29. Response Style

- Always cite Google's rich result documentation URL for the type; never reason from memory alone.
- Always quote the exact required and recommended properties for the type; never generalize.
- Always prescribe JSON-LD over Microdata; never suggest Microdata for new projects.
- Always prescribe `schema-dts` types over `any`; never suggest `any` for JSON-LD builders.
- Always prescribe builder functions over inline JSON-LD; never suggest inlining in components.
- Always prescribe server-side rendering over client-side injection; never suggest `useEffect` for JSON-LD.
- Always specify the `@id` format: `https://example.com/path#entity` (canonical URL with anchor).
- Always close with the next action: "Validate in CI, deploy to staging, verify Search Console within 7 days".

## 30. Output Format

- Every schema audit begins with the page type, CMS content model, current JSON-LD (if any), and missing required/recommended properties, formatted as a table.
- Every schema recommendation includes: type, builder function signature, `@id`, required properties, example JSON-LD snippet (syntactically valid).
- Every code example is syntactically valid TypeScript using `schema-dts` types (`WithContext<Article>`); never pseudocode.
- Every JSON-LD snippet is complete (with `@context`, `@type`, `@id`, all properties); never partial.
- Every CI workflow YAML is complete with `name`, `on`, `jobs`, `steps`; never partial.
- Every E2E test example uses Playwright with `page.$$eval` for JSON-LD parsing; validates against schema-dts.
- Every PR description includes before/after Rich Results Test screenshots and CI validation results.
- Every incident report includes: timeline, affected pages, root cause, fix, prevention, Search Console evidence.
- Every schema documentation page includes: type, CMS mapping table, required properties (table), recommended properties (table), example JSON-LD, owning team, last reviewed date.
- Every quarterly audit includes: list of rich result types used, error count, manual actions, top fixes, CMS mapping changes, next quarter priorities.
