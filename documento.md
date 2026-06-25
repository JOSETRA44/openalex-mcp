> ## Documentation Index
> Fetch the complete documentation index at: https://developers.openalex.org/llms.txt
> Use this file to discover all available pages before exploring further.

# Overview

[**OpenAlex**](https://openalex.org) is a fully open catalog of the global research system — hundreds of millions of scholarly works, authors, institutions, and more.

This is the **technical documentation for OpenAlex**, including the [**OpenAlex API**](/api-reference/introduction) and the [**data snapshot**](/download/overview). Here, you can learn how to set up your code to access OpenAlex's data. If you want to explore the data as a human, you may be more interested in [**OpenAlex Web**](https://help.openalex.org).

## Data

The OpenAlex dataset describes scholarly [*entities*](/api-reference/introduction) and how those entities are connected to each other. Types of entities include [works](/api-reference/works), [authors](/api-reference/authors), [sources](/api-reference/sources), [institutions](/api-reference/institutions), [topics](/api-reference/topics), [publishers](/api-reference/publishers), and [funders](/api-reference/funders).

Together, these make a huge web (or more technically, heterogeneous directed [graph](https://en.wikipedia.org/wiki/Graph_theory)) of hundreds of millions of entities and billions of connections between them all.

Learn more at our general help center article: [About the data](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data)

## Access

We offer a fast, modern REST API to get OpenAlex data programmatically. It's free but requires an API key (also free). Get yours at [openalex.org/settings/api](https://openalex.org/settings/api). With your free key, you get \$1/day of free usage. [Learn more](/api-reference/introduction)

Different API operations have different costs. See [authentication & pricing](/guides/authentication) for details.

There is also a complete database snapshot available to download. [Learn more about the data snapshot here.](/download/overview)

The API has a free daily limit of \$1/day, and the free snapshot is updated quarterly. If you need a higher API limit, **monthly snapshots**, or **daily change files** to keep a local copy in sync with ours, you'll need a [**paid plan**](https://openalex.org/pricing). Contact [sales@openalex.org](mailto:sales@openalex.org).

The web interface for OpenAlex, built directly on top of the API, is the quickest and easiest way to [get started with OpenAlex](https://help.openalex.org/getting-started).

## Why OpenAlex?

OpenAlex offers an open replacement for industry-standard scientific knowledge bases like Elsevier's Scopus and Clarivate's Web of Science. [Compared to](https://openalex.org/about#comparison) these paywalled services, OpenAlex offers significant advantages in terms of inclusivity, affordability, and availability.

OpenAlex is:

* **Big** — We have about twice the coverage of the other services, and have significantly better coverage of non-English works and works from the Global South.
* **Easy** — Our service is fast, modern, and well-documented.
* **Open** — Our complete dataset is free under the CC0 license, which allows for transparency and reuse.

Many people and organizations have already found great value using OpenAlex. Have a look at the [Testimonials](https://openalex.org/testimonials) to hear what they've said!

## Contact

For tech support and bug reports, please [submit a request](https://openalex.zendesk.com/hc/requests/new) or browse our [help center](https://openalex.org/help). You can also join the [OpenAlex user group](https://groups.google.com/g/openalex-users), and follow us on [Twitter (@OpenAlex\_org)](https://twitter.com/openalex_org) and [Mastodon](https://mastodon.social/@OpenAlex).

## Citation

If you use OpenAlex in research, please cite [this paper](https://arxiv.org/abs/2205.01833):

> Priem, J., Piwowar, H., & Orr, R. (2022). *OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts*. ArXiv. [https://arxiv.org/abs/2205.01833](https://arxiv.org/abs/2205.01833)

> ## Documentation Index
> Fetch the complete documentation index at: https://developers.openalex.org/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Query the OpenAlex dataset in 5 minutes

Let's use the OpenAlex API to find journal articles published by authors at Stanford University between 2010 and 2020. No login or API key required for basic queries.

<Tip>
  Install a JSON viewer extension like [JSONVue](https://chrome.google.com/webstore/detail/jsonvue/chklaanhfefbnpoihckbnefhakgolnmc) to make API responses easier to read in your browser.
</Tip>

## 1. Find an institution

Search for Stanford University using the institutions endpoint:

```bash theme={"dark"}
https://api.openalex.org/institutions?search=stanford
```

The first result has the ID we need:

```json theme={"dark"}
{
  "id": "https://openalex.org/I97018004",
  "ror": "https://ror.org/00f54p054",
  "display_name": "Stanford University",
  "country_code": "US",
  "type": "education"
}
```

## 2. Get a single entity

Fetch the full institution record by ID:

```bash theme={"dark"}
https://api.openalex.org/institutions/I97018004
```

This works for any entity type—works, authors, sources, etc.

## 3. Find works from Stanford

Filter works to show those with at least one Stanford author:

```bash theme={"dark"}
https://api.openalex.org/works?filter=institutions.id:I97018004
```

## 4. Filter by year and sort

Narrow to 2010-2020 and sort newest first:

```bash theme={"dark"}
https://api.openalex.org/works?filter=institutions.id:I97018004,publication_year:2010-2020&sort=publication_date:desc
```

## 5. Group by year

Get counts per year:

```bash theme={"dark"}
https://api.openalex.org/works?filter=institutions.id:I97018004,publication_year:2010-2020&group_by=publication_year
```

Response:

```json theme={"dark"}
[
  { "key": "2020", "key_display_name": "2020", "count": 18627 },
  { "key": "2019", "key_display_name": "2019", "count": 15933 },
  { "key": "2017", "key_display_name": "2017", "count": 14789 }
]
```

## 6. Semantic search (optional)

Find conceptually related works using AI:

```bash theme={"dark"}
https://api.openalex.org/works?search.semantic=machine+learning+in+healthcare&api_key=YOUR_KEY
```

This finds papers about "AI-driven diagnosis" even if they don't use the exact words "machine learning."

<Note>
  Semantic search requires an [API key](/guides/authentication). Basic filtering and searching is free.
</Note>

## 7. Download full text (optional)

For works with available content:

<CodeGroup>
  ```bash PDF theme={"dark"}
  https://content.openalex.org/works/W3038568908.pdf?api_key=YOUR_KEY
  ```

  ```bash TEI XML theme={"dark"}
  https://content.openalex.org/works/W3038568908.grobid-xml?api_key=YOUR_KEY
  ```
</CodeGroup>

Check the `has_content.pdf` filter to find downloadable works.

## Next steps

<CardGroup cols={2}>
  <Card title="Works" icon="file-lines" href="/api-reference/works">
    Journal articles, books, datasets, theses
  </Card>

  <Card title="Authors" icon="user" href="/api-reference/authors">
    Researchers and their publications
  </Card>

  <Card title="Filtering" icon="filter" href="/guides/filtering">
    Narrow results with 150+ filter options
  </Card>

  <Card title="Recipes" icon="book" href="/guides/recipes">
    Common API patterns and examples
  </Card>
</CardGroup>

All data is [CC0 licensed](https://creativecommons.org/publicdomain/zero/1.0/) — free to access and share.
> ## Documentation Index
> Fetch the complete documentation index at: https://developers.openalex.org/llms.txt
> Use this file to discover all available pages before exploring further.

# Authentication & Pricing

> API keys, pricing tiers, and usage limits

OpenAlex data is and will remain available at no cost. Our [data snapshot](/download/overview#openalex-snapshot) is totally free for bulk download. The API is a freemium service with free daily usage—$0.10/day with no key, or 10× that ($1/day) with a [free API key](#getting-an-api-key)—and after that you pay for what you use. [We sell services, not data.](https://openscholarlyinfrastructure.org/)

## Getting an API Key

To use the API at scale, you need a key. It's free—just [make an account](https://openalex.org/) (takes 30 seconds) and copy your key from [openalex.org/settings/api](https://openalex.org/settings/api). Then add `api_key=YOUR_KEY` to your API calls:

```bash theme={"dark"}
curl "https://api.openalex.org/works?api_key=YOUR_KEY"
```

## What You Can Do for Free Every Day

Your free API key gives you \$1 of free usage every day. With that, you can do a mix of:

| Action              | Calls     | Results   | Example                       |
| ------------------- | --------- | --------- | ----------------------------- |
| Get a single entity | Unlimited | Unlimited | Look up a work by DOI         |
| List+filter         | 10,000    | 1,000,000 | All works from MIT in 2024    |
| Search              | 1,000     | 100,000   | Full-text search for "CRISPR" |
| Content download    | 100       | 100 PDFs  | Download a paper's full text  |

Without a key you get \$0.10/day—a tenth of the above, enough to try the API. [Get a free key](#getting-an-api-key) for 10× the budget.

For full details on endpoint pricing, common activity costs, usage limit headers, query limits, and usage tips, see [Authentication & Pricing](/api-reference/authentication) in the API Reference.