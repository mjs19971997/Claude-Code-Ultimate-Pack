# Schema.org Vocabulary and Entity Modeling

Reference for the Schema.org vocabulary and JSON-LD syntax: types and properties, value formats, `@id` and `@graph` entity modeling, common type recipes and typed builders. This file absorbs the former schema-org-expert skill. Verified against Schema.org release 30.1 (2026-09-16, from the project's versions.json), schema-dts 2.1.0 and the JSON-LD 1.1 specification (2026-10). Google-specific eligibility is covered in [structured-data.md](structured-data.md).

## 1. Vocabulary basics

- Schema.org is a shared vocabulary of types (`Product`, `Article`, `Organization`) arranged in a hierarchy that starts at `Thing`, and of properties with expected value types. A type inherits the properties of its parents; use the most specific type that fits (`NewsArticle` over `Article`, `Hotel` over `LodgingBusiness`).
- Releases are versioned and dated; the current one at this writing is 30.1. Terms in the pending area are not stable. Terms are used from `https://schema.org/` regardless of the release.
- Syntaxes: JSON-LD (recommended), Microdata, RDFa. Google supports all three but documents JSON-LD as preferred; JSON-LD keeps markup separate from HTML and is easier to generate and test.
- Properties are optional unless a consumer (Google, Bing, an app) requires them; "valid Schema.org" and "eligible for a Google feature" are different checks.
- `@context` is `"https://schema.org"` (HTTPS form).

## 2. JSON-LD syntax essentials

| Keyword | Meaning |
|---|---|
| `@context` | Maps terms to the vocabulary; required once at the top of the document |
| `@type` | Type name, or an array for multiple types (`["Organization", "OnlineStore"]`) |
| `@id` | Global identifier (an IRI) for the node; lets other nodes reference it |
| `@graph` | Array of nodes in one document |
| `@language`, `@value` | Language-tagged strings: `{"@language": "de", "@value": "Hallo"}` |

- A property may hold one value or an array. Use arrays for multi-valued properties (`image`, `sameAs`, `author`).
- A reference to another node is `{"@id": "https://example.com/#org"}`; it carries no other data.
- Node identifiers are IRIs, usually the page URL plus a fragment: `https://example.com/#organization`, `https://example.com/blog/post#article`. Keep them stable across deploys and unique.
- Use absolute URLs for `url`, `image`, `logo`, `sameAs`, `item` and other URL values.
- Do not use comments or trailing commas; the output must be valid JSON.

## 3. Value formats

| Kind | Format | Example |
|---|---|---|
| Date | ISO 8601 date | `"2026-10-30"` |
| DateTime | ISO 8601 with offset | `"2026-10-30T09:30:00+01:00"` |
| Duration | ISO 8601 duration | `"PT1H30M"` |
| URL | Absolute URL | `"https://example.com/p"` |
| Enumeration | Full IRI of the member | `"https://schema.org/InStock"` |
| Price | Number or numeric string, no symbol or thousand separators | `"29.99"` |
| Currency | ISO 4217 code | `"EUR"` |
| Country | ISO 3166-1 alpha-2 | `"DE"` |
| Language | IETF BCP 47 | `"en-GB"` |
| Quantity | `QuantitativeValue` with `value` and `unitCode` (UN/CEFACT code) | `{"@type":"QuantitativeValue","value":2,"unitCode":"KGM"}` |

## 4. Entity modeling with `@graph`

Describe each real-world entity once and connect entities by `@id`:

- Site-wide entities (Organization, WebSite) are defined in one place and referenced from every page.
- Each page defines its own WebPage node and the main entity (Article, Product, Event) and links them with `mainEntityOfPage`, `isPartOf`, `author`, `publisher`, `breadcrumb`.
- Avoid copy-pasting the full Organization object into every Article; reference it by `@id`.
- If a node appears under two parents, define it once in `@graph` and reference it elsewhere.

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://www.example.com/#organization",
      "name": "Example Labs",
      "url": "https://www.example.com/",
      "logo": {
        "@type": "ImageObject",
        "url": "https://www.example.com/logo-512.png",
        "width": 512,
        "height": 512
      },
      "sameAs": [
        "https://www.linkedin.com/company/example-labs",
        "https://github.com/example-labs"
      ]
    },
    {
      "@type": "WebSite",
      "@id": "https://www.example.com/#website",
      "url": "https://www.example.com/",
      "name": "Example Labs",
      "publisher": {"@id": "https://www.example.com/#organization"},
      "inLanguage": "en-GB"
    },
    {
      "@type": "Person",
      "@id": "https://www.example.com/team/ada#person",
      "name": "Ada Example",
      "url": "https://www.example.com/team/ada",
      "worksFor": {"@id": "https://www.example.com/#organization"}
    },
    {
      "@type": "WebPage",
      "@id": "https://www.example.com/blog/indexing-basics#webpage",
      "url": "https://www.example.com/blog/indexing-basics",
      "name": "Indexing basics",
      "isPartOf": {"@id": "https://www.example.com/#website"},
      "breadcrumb": {"@id": "https://www.example.com/blog/indexing-basics#breadcrumb"},
      "primaryImageOfPage": {"@id": "https://www.example.com/blog/indexing-basics#primaryimage"}
    },
    {
      "@type": "ImageObject",
      "@id": "https://www.example.com/blog/indexing-basics#primaryimage",
      "url": "https://www.example.com/img/indexing-1200.jpg",
      "width": 1200,
      "height": 630
    },
    {
      "@type": "BreadcrumbList",
      "@id": "https://www.example.com/blog/indexing-basics#breadcrumb",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.example.com/"},
        {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://www.example.com/blog"},
        {"@type": "ListItem", "position": 3, "name": "Indexing basics"}
      ]
    },
    {
      "@type": "Article",
      "@id": "https://www.example.com/blog/indexing-basics#article",
      "headline": "Indexing basics",
      "datePublished": "2026-09-01T08:00:00+00:00",
      "dateModified": "2026-10-15T10:30:00+00:00",
      "image": {"@id": "https://www.example.com/blog/indexing-basics#primaryimage"},
      "author": {"@id": "https://www.example.com/team/ada#person"},
      "publisher": {"@id": "https://www.example.com/#organization"},
      "mainEntityOfPage": {"@id": "https://www.example.com/blog/indexing-basics#webpage"}
    }
  ]
}
```

Notes: consumers resolve references within the same document. Some validators and consumers handle fully nested objects better than `@id` references only; when a Google feature requires a property (for example `author` with `name`), check with the Rich Results Test and nest the data if the reference is not recognized.

## 5. Common types and key properties

| Type | Use for | Key properties |
|---|---|---|
| `Organization` (and `OnlineStore`, `NGO`, `Corporation`) | The business or institution | `name`, `url`, `logo`, `sameAs`, `contactPoint`, `address`, `foundingDate`, `legalName`, `identifier` |
| `LocalBusiness` subtypes | Physical locations | `name`, `address` (`PostalAddress`), `telephone`, `openingHoursSpecification`, `geo`, `priceRange`, `url` |
| `Person` | Authors, team members | `name`, `url`, `sameAs`, `jobTitle`, `worksFor` |
| `WebSite`, `WebPage` and subtypes (`AboutPage`, `ContactPage`, `CollectionPage`, `ProfilePage`, `FAQPage`) | Site and page identity | `url`, `name`, `isPartOf`, `inLanguage`, `breadcrumb`, `primaryImageOfPage` |
| `Article`, `NewsArticle`, `BlogPosting` | Editorial content | `headline`, `image`, `datePublished`, `dateModified`, `author`, `publisher`, `articleSection` |
| `Product` | Goods and services sold | `name`, `image`, `description`, `sku`, `gtin`, `brand`, `offers`, `aggregateRating`, `review` |
| `Offer`, `AggregateOffer` | Price and availability | `price`, `priceCurrency`, `availability`, `url`, `priceValidUntil`, `itemCondition`, `seller`, `shippingDetails`, `hasMerchantReturnPolicy` |
| `Event` | Dated events | `name`, `startDate`, `endDate`, `eventStatus`, `eventAttendanceMode`, `location` (`Place` or `VirtualLocation`), `offers`, `organizer` |
| `JobPosting` | Open roles | `title`, `description`, `datePosted`, `validThrough`, `hiringOrganization`, `jobLocation`, `baseSalary`, `employmentType` |
| `Recipe` | Cooking content | `name`, `image`, `recipeIngredient`, `recipeInstructions`, `totalTime`, `nutrition`, `aggregateRating` |
| `VideoObject` | Videos | `name`, `description`, `thumbnailUrl`, `uploadDate`, `duration`, `contentUrl`, `embedUrl` |
| `BreadcrumbList` / `ListItem` | Breadcrumb trails | `itemListElement` with `position`, `name`, `item` |
| `SoftwareApplication`, `WebApplication` | Apps | `name`, `applicationCategory`, `operatingSystem`, `offers`, `aggregateRating` |
| `Course`, `Dataset`, `Book`, `Movie`, `Review`, `Rating` | Domain-specific content | See the type page for properties |
| `PostalAddress`, `GeoCoordinates`, `Place` | Locations | `streetAddress`, `addressLocality`, `postalCode`, `addressCountry`, `latitude`, `longitude` |

## 6. Modeling rules

- Mark up only what the page shows. Properties must describe visible content; do not add hidden entities, invented reviews, or prices that differ from the page.
- One main entity per page. Supporting entities (organization, author, breadcrumb) are separate nodes.
- Use `sameAs` for authoritative profile URLs of the same entity (official social profiles, Wikipedia or Wikidata page), not for related pages.
- Use `identifier`, `sku`, `gtin`/`gtin13`, `mpn` to identify products; `brand` as `Brand` with `name`.
- `Offer.availability` takes a full IRI from `ItemAvailability`; `OfferItemCondition` for `itemCondition`.
- Model variants (`ProductGroup` with `hasVariant`) when a page represents one product with sizes or colors; check Google's current variant guidance.
- Do not mix unrelated vocabularies in the same object; extend with `additionalProperty` / `PropertyValue` when no property fits.
- Language: use `inLanguage` and language-tagged values for multilingual sites; keep one node per language page.

## 7. TypeScript builders with schema-dts

`schema-dts` (2.1.0) provides types for all Schema.org terms: `WithContext<T>` for a single root node and `Graph` for a `@graph` document. Wrong property names or value shapes become compile-time errors.

```ts
import type {Graph, Organization, WebSite} from 'schema-dts';

const ORIGIN = 'https://www.example.com';

export const orgId = `${ORIGIN}/#organization`;
export const siteId = `${ORIGIN}/#website`;

export function organization(): Organization {
  return {
    '@type': 'Organization',
    '@id': orgId,
    name: 'Example Labs',
    url: `${ORIGIN}/`,
    logo: `${ORIGIN}/logo-512.png`,
    sameAs: ['https://github.com/example-labs'],
  };
}

export function website(): WebSite {
  return {
    '@type': 'WebSite',
    '@id': siteId,
    url: `${ORIGIN}/`,
    name: 'Example Labs',
    publisher: {'@id': orgId},
  };
}

export function graph(...nodes: Graph['@graph'][number][]): Graph {
  return {'@context': 'https://schema.org', '@graph': nodes};
}
```

- Builders take plain domain objects (CMS entries, database rows), never raw request input; map to Schema.org in one place.
- Build absolute URLs through one helper that uses a configured origin.
- Unit-test builders with fixtures and assert required properties; see [structured-data.md](structured-data.md) for tests and validation.
- Serialize with an escaping function before embedding in HTML (see SKILL.md Examples).

## 8. Other uses of the vocabulary

- Bing and other consumers read Schema.org markup for entities and product data; Google uses it for rich results and general understanding. Markup also helps knowledge graph reconciliation through consistent `@id`, `sameAs` and `name`.
- Validators: Schema Markup Validator (validator.schema.org) checks vocabulary correctness for any type; Google's Rich Results Test checks only Google-supported features.
- Open Graph and Twitter Card tags are separate protocols for link previews; do not duplicate or mix their properties into JSON-LD.
- Microdata or RDFa already in templates can stay; avoid duplicating the same entity in two syntaxes on one page.
