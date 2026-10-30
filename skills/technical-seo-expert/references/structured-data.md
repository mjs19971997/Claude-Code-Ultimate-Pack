# Structured Data for Search

Implementing structured data for Google and Bing: which features are still eligible and which were retired, required properties for common features, safe server-side implementation with JSON-LD, validation and monitoring. This file absorbs the former structured-data-expert skill. Verified against Schema.org release 30.1, schema-dts 2.1.0, Next.js 16 JSON-LD guide and secondary reporting on Google's 2023 to 2026 structured data changes (2026-10). Google's documentation hosts were not reachable while writing, so feature status below is marked "check the current docs"; the Search Central structured data gallery is the authority.

## 1. Principles

- Structured data describes content that is already visible on the page. It must be accurate, current and relevant; hidden, misleading or fabricated markup can trigger a manual action and loses rich result eligibility.
- Valid markup does not guarantee a rich result. Google decides per query and page quality.
- JSON-LD in the page head or body is the recommended format. Microdata and RDFa are accepted.
- One consistent source of truth: generate markup from the same data that renders the page (price, availability, dates, ratings), so values cannot drift.
- Markup for a feature must match the page type: Product markup belongs on a page about one product, not a category listing; Recipe markup on a recipe page.

## 2. Feature status (check the current docs)

Google has been simplifying search results. Reported changes:

| Feature | Status |
|---|---|
| HowTo | Rich results removed from mobile and desktop in 2023; no rich result in Google Search |
| FAQ | Limited to well-known government and health sites in August 2023; reported discontinued for all sites in 2026 (Search Console report and Rich Results Test support removed in stages). FAQPage markup remains valid Schema.org |
| Book actions, Course info, ClaimReview, Estimated salary, Learning video, Special announcement, Vehicle listing | Announced June 2025 as phased out of Search results |
| Practice problem | Deprecated starting January 2026 |
| Sitelinks search box | Reported retired in late 2024 |
| Dataset | Used by Dataset Search only, not standard results |

Features documented in the gallery and still commonly used (confirm each before building): Article, Breadcrumb, Carousel (ItemList), Discussion forum, Employer aggregate rating, Event, Image metadata, Job posting, Local business, Merchant listing, Movie, Organization, Paywalled content, Product snippets and product variants, Profile page, Q&A, Recipe, Review snippet, Software app, Vacation rental, Video.

When a feature is retired the Schema.org type usually stays valid and harmless; it only stops producing a Google rich result. Keep markup that describes real content and benefits other consumers; stop promising rich results for retired features.

## 3. Required and recommended properties (check the current docs)

| Feature | Required for eligibility | Commonly recommended |
|---|---|---|
| Article | None strictly required; supply what applies | `headline`, `image`, `datePublished`, `dateModified`, `author` (`name`, `url`) |
| Breadcrumb | `itemListElement` with `ListItem` `position`, `name`; `item` URL for all except the last | |
| Product snippet | `name` plus at least one of `review`, `aggregateRating`, `offers` | `image`, `description`, `sku`, `brand`, `gtin` |
| Merchant listing | `name`, `image`, `offers` with `price` and `priceCurrency` | `availability`, `shippingDetails`, `hasMerchantReturnPolicy`, `brand`, `sku` |
| Review snippet | `itemReviewed`, `reviewRating` (`ratingValue`), `author` | `bestRating`, `worstRating` |
| Event | `name`, `startDate`, `location` | `endDate`, `eventStatus`, `eventAttendanceMode`, `offers`, `image`, `organizer` |
| Job posting | `title`, `description`, `datePosted`, `hiringOrganization`, `jobLocation` (or remote requirements) | `validThrough`, `baseSalary`, `employmentType` |
| Local business | `name`, `address` | `telephone`, `openingHoursSpecification`, `geo`, `url`, `priceRange` |
| Recipe | `name`, `image` | `recipeIngredient`, `recipeInstructions`, `totalTime`, `nutrition`, `aggregateRating`, `video` |
| Video | `name`, `thumbnailUrl`, `uploadDate` | `description`, `duration`, `contentUrl`, `embedUrl` |
| Organization | None strictly required | `name`, `url`, `logo`, `sameAs`, `contactPoint`, `address` |
| Q&A, Profile page, Discussion forum | See the gallery pages for the exact structure | |

Rules of thumb: `price` is a plain number without currency symbol or separators; `availability` is a full Schema.org IRI; dates are ISO 8601; images are crawlable absolute URLs, not blocked by robots.txt.

## 4. Policy rules that cause problems

- Ratings and reviews must be real, about the item on the page, and visible. Do not add reviews written by the site about itself to Organization or LocalBusiness for star results ("self-serving" reviews are not eligible).
- Do not mark up content that users cannot see (hidden text, other pages' content, off-screen blocks).
- Price, currency and availability in markup must match the visible offer and the checkout.
- Do not mark up a whole site's reviews on every page; place them on the page that shows the items.
- Do not use markup on pages that only link to detail pages unless the feature supports lists (Carousel/ItemList).
- Keep markup in sync after changes: a sold-out product should not say `InStock`.

## 5. Implementation architecture

```
CMS or database row
  -> domain mapper (typed)
  -> schema builder (schema-dts types)
  -> serializeJsonLd() with escaping
  -> <script type="application/ld+json"> in server-rendered HTML
```

- Render JSON-LD on the server (server component, template, SSG). Google can read JSON-LD that JavaScript injects, but server-rendered markup is available at first parse, works for other consumers and avoids hydration mismatches. Do not inject it in `useEffect`.
- Keep builders in one module per template (`product.ts`, `article.ts`, `breadcrumb.ts`), typed with schema-dts, covered by unit tests.
- Put site-wide entities (Organization, WebSite) in the layout once; page templates add their own nodes and reference the site nodes by `@id`.
- Escape on output, not on input: escaping inside `serializeJsonLd` protects every call site.
- Normalize CMS data first: trim whitespace, strip HTML from text fields, convert rich text to plain text for `description`, make URLs absolute, drop empty properties rather than emitting empty strings.

## 6. Safe serialization and CSP

`JSON.stringify` does not escape `<`. A field containing `</script><script>alert(1)</script>` would end the JSON-LD element and start an executable script. Prevent it by escaping before output:

```ts
export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}
```

- The escaped text is still valid JSON; any JSON parser (including Google's) reads the original characters back.
- Use it in every framework: React `dangerouslySetInnerHTML={{__html: serializeJsonLd(data)}}`, Astro `<script type="application/ld+json" set:html={serializeJsonLd(data)} />`, or plain template strings in server-side templates. The Next.js JSON-LD guide recommends the same `<` replacement.
- Content Security Policy: `<script type="application/ld+json">` is a data block. Browsers do not execute it, and `script-src` does not need `'unsafe-inline'` or a nonce for it. A strict policy can stay in place, for example:

```
Content-Security-Policy: default-src 'self'; script-src 'nonce-R4nd0m' 'strict-dynamic'; object-src 'none'; base-uri 'none'
```

- If JSON-LD must be added by JavaScript (a tag manager or client code), that script is executable code: give it a per-request nonce (`<script nonce="R4nd0m">`) or a hash, and prefer moving the injection to the server.
- Generate a fresh random nonce for every response; never reuse a static value.

## 7. Validation workflow

1. During development: Schema Markup Validator (validator.schema.org) for vocabulary correctness of any type; Rich Results Test (search.google.com/test/rich-results) for Google feature eligibility, using the live URL or pasted code.
2. Pre-release: unit tests on builders, and an end-to-end test that fetches rendered pages (see below).
3. After release: Search Console URL Inspection (detected structured data on the live page) and the rich result reports for the feature (errors, warnings, valid items); watch for new errors after template changes.
4. Errors make the item ineligible; warnings concern optional properties and can usually be fixed later.
5. Compare Search Console valid-item counts to the number of pages you expect to carry markup; a sudden drop usually means a template regression.

## 8. Automated tests

Unit test for escaping (Node's built-in test runner):

```ts
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {serializeJsonLd} from './jsonld';

test('serializeJsonLd neutralizes script breakout', () => {
  const payload = {name: '</script><script>alert(1)</script>'};
  const out = serializeJsonLd(payload);
  assert.ok(!out.includes('<'));
  assert.deepEqual(JSON.parse(out), payload);
});
```

End-to-end check of a rendered page (Playwright):

```ts
import {test, expect} from '@playwright/test';

test('product page exposes consistent Product JSON-LD', async ({page}) => {
  await page.goto('/products/example');

  const blocks = await page.locator('script[type="application/ld+json"]').allTextContents();
  expect(blocks.length).toBeGreaterThan(0);

  const nodes = blocks.map((b) => JSON.parse(b)).flatMap((d) => d['@graph'] ?? [d]);
  const product = nodes.find((n) => n['@type'] === 'Product');
  expect(product, 'Product node').toBeTruthy();
  expect(product.name).toBeTruthy();

  const offer = [product.offers].flat()[0];
  expect(offer.priceCurrency).toMatch(/^[A-Z]{3}$/);
  expect(Number(offer.price)).toBeGreaterThan(0);
  expect(offer.availability).toMatch(/^https:\/\/schema\.org\//);

  // Markup must match what the user sees.
  await expect(page.locator('[data-testid="price"]')).toContainText(String(offer.price));
  await expect(page.locator('h1')).toContainText(product.name);
});
```

## 9. Examples

Product with offer, shipping and return policy (merchant listing eligibility; values are examples):

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "@id": "https://www.example.com/products/trail-shoe#product",
  "name": "Trail Shoe",
  "image": ["https://www.example.com/img/trail-shoe-1200.jpg"],
  "description": "Lightweight trail running shoe with a grippy outsole.",
  "sku": "TS-100",
  "brand": {"@type": "Brand", "name": "Example Sports"},
  "offers": {
    "@type": "Offer",
    "url": "https://www.example.com/products/trail-shoe",
    "price": "119.00",
    "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock",
    "itemCondition": "https://schema.org/NewCondition",
    "shippingDetails": {
      "@type": "OfferShippingDetails",
      "shippingRate": {"@type": "MonetaryAmount", "value": "4.95", "currency": "EUR"},
      "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "DE"},
      "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "handlingTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY"},
        "transitTime": {"@type": "QuantitativeValue", "minValue": 1, "maxValue": 3, "unitCode": "DAY"}
      }
    },
    "hasMerchantReturnPolicy": {
      "@type": "MerchantReturnPolicy",
      "applicableCountry": "DE",
      "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
      "merchantReturnDays": 30,
      "returnMethod": "https://schema.org/ReturnByMail",
      "returnFees": "https://schema.org/FreeReturn"
    }
  }
}
```

Add `aggregateRating` only when real, visible ratings from users exist on the page, with `ratingValue` and `reviewCount` (or `ratingCount`) that match what is shown.

Job posting:

```json
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Backend Engineer",
  "description": "<p>Build and operate our payments APIs.</p>",
  "datePosted": "2026-10-01",
  "validThrough": "2026-12-01T00:00:00+00:00",
  "employmentType": "FULL_TIME",
  "hiringOrganization": {
    "@type": "Organization",
    "name": "Example Labs",
    "sameAs": "https://www.example.com/",
    "logo": "https://www.example.com/logo-512.png"
  },
  "jobLocation": {
    "@type": "Place",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "1 Example Street",
      "addressLocality": "Berlin",
      "postalCode": "10115",
      "addressCountry": "DE"
    }
  },
  "baseSalary": {
    "@type": "MonetaryAmount",
    "currency": "EUR",
    "value": {"@type": "QuantitativeValue", "minValue": 70000, "maxValue": 90000, "unitText": "YEAR"}
  }
}
```

Next.js server component that renders markup safely (the helper is in section 6):

```tsx
import {serializeJsonLd} from '@/lib/seo/jsonld';
import {productJsonLd} from '@/lib/seo/schema/product';

export default async function ProductPage({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  const product = await getProduct(slug);
  return (
    <main>
      <h1>{product.name}</h1>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{__html: serializeJsonLd(productJsonLd(product))}}
      />
    </main>
  );
}
```

## 10. Monitoring and maintenance

- Track rich result report counts (valid, with warnings, errors) in Search Console per feature; set alerts for sudden drops.
- Re-run Rich Results Test on one URL per template in CI after each template change.
- Review the Search Central structured data gallery and changelog on a schedule (for example quarterly) to catch retired or changed features.
- Keep a registry of which templates emit which types so feature retirements can be handled in one place (stop emitting only where no other consumer benefits).
- For commerce, keep Merchant Center feeds and on-page markup consistent; mismatched price or availability can cause disapprovals.
- When a feature is retired, you do not need to remove valid markup; remove it only if it costs maintenance or conflicts with page content.
