# Opsera website analytics, in plain text

The data behind the dashboard at https://puravbhandari-gif.github.io/opsera-analytics-dashboard/, written for AI assistants such as Claude.
Every number here also appears on the dashboard. We rebuild these files every Monday morning, India time. Last rebuilt from data pulled 2026-10-27.

## How to answer questions

- Read this guide first, then open only the files a question needs. Every file is a small CSV with a header row.
- Weeks run Monday to Sunday. Months are calendar months. `period_not_finished` is "yes" for a week or month still under way.
- Google Analytics and HubSpot dates follow US Pacific time. LinkedIn exports use UTC.
- Never add numbers from different sources together (for example Google Analytics visits and Search Console clicks). Each file and column says its source.
- "Without email robots" leaves out visits by email link checkers: visits with no engagement landing on email subscription pages (/hs/preferences-center), from Cupertino, Palo Alto, Garner or Sunnyvale, or from Safari on a Mac desktop. All visits stays as Google Analytics counts it.
- "Visits" are Google Analytics sessions. "Engaged visits" are visits where someone stayed 10+ seconds, saw 2+ pages or filled a form. They leave out most email robots.
- Form fills count the HubSpot form event in Google Analytics. We leave out job application forms everywhere.
- Asset downloads are form fills on pages under /resources/report/, /resources/white-papers/, /resources/ebooks/ or /resources/comparison-guides/. They're part of "other forms".
- Deals exist as weekly and monthly totals, and as 1 line per marketing deal in deals_one_line_each.csv, without company or person names. Closed Lost deals stay out, and there are no daily deal numbers.
- When the dashboard compares periods, it compares the last full week with the week before, or this month so far with the whole of last month.
- A page in the page files is its address on opsera.ai, so `/pricing` is https://opsera.ai/pricing. Page titles are in the page_titles files.
- We split page and page title files by part of the site: blog, resources, knowledge base and other. Big ones also split by quarter, month or week, as the file name says.
- Questions about a campaign: use the campaign files (the utm_campaign in Google Analytics). Search Console counts Google clicks by page, so campaigns don't have them.
- Questions about a channel: use customer_journey_funnel (journey channels) or visit_sources (Google Analytics channel groups).
- If a question needs something these files don't have, say so instead of guessing.

## Date ranges

- Google Analytics and HubSpot: 2026-04-01 to 2026-10-26.
- Search Console (Google search): 2026-04-01 to 2026-10-25. It runs about 2 days behind.
- LinkedIn company page: 2026-07-01 to 2026-10-25. LinkedIn Kumar: 2026-07-01 to 2026-10-27, the last day still being counted when exported.
- YouTube: 2026-04-01 to 2026-10-24.
- Kahoots and Infrasity: July to September 2026, as they reported it.

## Customer journey tab

How marketing turns website visits into demo requests, meetings and deals. The funnel has 6 steps. Google Analytics counts visits, demo page views and demo form fills. HubSpot counts new contacts, meetings and deals. A contact is someone who first filled in the demo form. Meetings and deals count only after sign-up, never with existing customers. A later step can be bigger than the step before because the 2 tools count differently. For Google search, every step ends on Search Console's last day, and the first 2 columns are Search Console. "All channels" visits match the Website visits tab.

- [customer_journey_funnel_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_funnel_by_month.csv): The funnel for each channel, by month. Sources: Search Console for the 2 Google columns, Google Analytics from visits to demo form, HubSpot from contacts to deals. 63 rows.
- [customer_journey_funnel_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_funnel_by_week.csv): The funnel for each channel, by week. Sources: Search Console for the 2 Google columns, Google Analytics from visits to demo form, HubSpot from contacts to deals. 278 rows.
- [customer_journey_summary_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_summary_by_month.csv): Customer journey tab, top numbers, by month. Sources: Google Analytics (demo requests), HubSpot (meetings and deals). 7 rows.
- [customer_journey_summary_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_summary_by_week.csv): Customer journey tab, top numbers, by week. Sources: Google Analytics (demo requests), HubSpot (meetings and deals). 31 rows.

## Website visits tab

- [website_visits_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/website_visits_by_month.csv): Website visits tab, by month. Source: Google Analytics. 7 rows.
- [website_visits_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/website_visits_by_week.csv): Website visits tab, by week. Source: Google Analytics. 31 rows.
- [visit_sources_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/visit_sources_by_month.csv): Where visits came from (Google Analytics channel groups), by month. Source: Google Analytics. 75 rows.
- [visit_sources_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/visit_sources_by_week.csv): Where visits came from (Google Analytics channel groups), by week. Source: Google Analytics. 270 rows.

## Leads tab

Demo requests are form fills on /demo. Contact forms are on /contact. The Gartner offer is /gartner-symposium/free-modernization. Event sign-ups are /events/ pages, /gartner-symposium and /github-universe-happy-hour. Everything else is other forms. Before October, the old site sent some homepage and contact form fills only to Google, so earlier months look low. Luma event sign-ups don't show here.

- [leads_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/leads_by_month.csv): Leads tab: form fills by kind of form, by month. Source: Google Analytics (HubSpot form event). 7 rows.
- [leads_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/leads_by_week.csv): Leads tab: form fills by kind of form, by week. Source: Google Analytics (HubSpot form event). 31 rows.

## Events tab

Each webinar, roundtable and event since 1 Apr, and the HubSpot sign-up lists, each on its own.

- [events_one_row_each.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/events_one_row_each.csv): Each webinar, roundtable and event since 1 Apr 2026. Sign-ups, attended and meetings come from HubSpot; event page form fills from Google Analytics. Never add the two together. Blank means no data. 8 rows.
- [hubspot_event_lists.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/hubspot_event_lists.csv): Event sign-up lists in HubSpot, each on its own (never added together). Source: HubSpot. 4 rows.

## Campaigns tab

Each campaign's link-tag visits and HubSpot emails and deals (the campaigns file below the Look up section), and Google Ads by campaign.

- [google_ads_by_campaign.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_ads_by_campaign.csv): Google Ads spend and ad clicks (counted by Google Ads) with visits and demo requests (counted by Google Analytics), per campaign per month. Brand search visits and demo requests from 16 Jun 2026 are too low because of a tracking problem. Source: Google Analytics, opsera.ai 2026, linked to Google Ads. 12 rows.

## Pages, campaigns and assets (the Look up tab)

Visits count people who landed on the page from outside the site. Page files list a page in a period only when it had a visit, form fill or Google click.

- pages_by_month_blog, split to stay small: Pages under /blog/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-05.csv), [2026-06](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-06.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-09.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-Q4.csv).
- [pages_by_month_knowledge_base.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_knowledge_base.csv): Pages under /knowledge-base/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. 278 rows.
- pages_by_month_main, split to stay small: Main pages 1 level deep (the homepage, /demo, /pricing and the like) by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_main_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_main_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_main_2026-Q4.csv).
- pages_by_month_other, split to stay small: Pages in other sections such as /newsroom/ and /changelog/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-05.csv), [2026-06](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-06.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-09.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-Q4.csv).
- pages_by_month_resources, split to stay small: Pages under /resources/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q4.csv).
- pages_by_week_blog, split to stay small: Pages under /blog/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-05.csv), [2026-06-01](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-01.csv), [2026-06-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-08.csv), [2026-06-15](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-15.csv), [2026-06-22](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-22.csv), [2026-06-29](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-29.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-07.csv), [2026-08-03](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08-03.csv), [2026-08-10](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08-10.csv), [2026-08-17](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08-17.csv), [2026-08-24](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08-24.csv), [2026-08-31](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08-31.csv), [2026-09-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-07.csv), [2026-09-14](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-14.csv), [2026-09-21](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-21.csv), [2026-09-28](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-28.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-Q4.csv).
- pages_by_week_knowledge_base, split to stay small: Pages under /knowledge-base/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q4.csv).
- pages_by_week_main, split to stay small: Main pages 1 level deep (the homepage, /demo, /pricing and the like) by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-05.csv), [2026-06](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-06.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-09.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-Q4.csv).
- pages_by_week_other, split to stay small: Pages in other sections such as /newsroom/ and /changelog/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-05.csv), [2026-06-01](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-01.csv), [2026-06-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-08.csv), [2026-06-15](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-15.csv), [2026-06-22](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-22.csv), [2026-06-29](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-29.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-07.csv), [2026-08-03](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08-03.csv), [2026-08-10](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08-10.csv), [2026-08-17](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08-17.csv), [2026-08-24](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08-24.csv), [2026-08-31](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08-31.csv), [2026-09-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-07.csv), [2026-09-14](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-14.csv), [2026-09-21](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-21.csv), [2026-09-28](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-28.csv), [2026-10-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-05.csv), [2026-10-12](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-12.csv), [2026-10-19](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-19.csv), [2026-10-26](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-26.csv).
- pages_by_week_resources, split to stay small: Pages under /resources/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-05.csv), [2026-06](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-06.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-09.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-Q4.csv).
- [page_titles_blog.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_blog.csv): The title of each page: pages under /blog/. Source: Google Analytics. 276 rows.
- [page_titles_knowledge_base.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_knowledge_base.csv): The title of each page: pages under /knowledge-base/. Source: Google Analytics. 80 rows.
- [page_titles_main.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_main.csv): The title of each page: main pages 1 level deep (the homepage, /demo, /pricing and the like). Source: Google Analytics. 446 rows.
- page_titles_other, split to stay small: The title of each page: pages in other sections such as /newsroom/ and /changelog/. Source: Google Analytics. Parts: [part 1: /_hcms/preview/template/multi to /wp-json/wp/v2/posts/681](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_other_part1.csv), [part 2: /wp-json/wp/v2/posts/683 to /wp/login](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_other_part2.csv).
- [page_titles_resources.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_resources.csv): The title of each page: pages under /resources/. Source: Google Analytics. 94 rows.
- [campaigns_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_by_month.csv): Every campaign (utm_campaign) with visits or form fills, by month. Source: Google Analytics. 301 rows.
- [campaigns_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_by_week.csv): Every campaign (utm_campaign) with visits or form fills, by week. Source: Google Analytics. 486 rows.
- [campaigns_since_1_apr.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_since_1_apr.csv): Each campaign since 1 Apr 2026: visits, engaged visits and form fills from Google Analytics link tags (to 2026-10-26), emails and deals from HubSpot. Never add the two sources together. A deal belongs to the campaign its person first came in on. Target-account campaigns, sales outreach codes and spam sites are left out. 219 rows.

## Content tab

One row per blog post, report, white paper, eBook, guide (knowledge base article) and comparison page. content_pieces lists each piece with its type; its visits, form fills and Google clicks are in the page files above. A deal counts for a piece when the contact's first page or first form was that piece (see deals_one_line_each.csv).

- content_pieces, split to stay small: Content tab: each blog post, report, white paper, eBook, guide and comparison page with its type. Their numbers are in the page files. Parts: [part 1: /blog/10-must-have-salesforce-devops-tools-and-how-to-orchestrate-them-right to /resources/comparison-guides/opsera-vs-harness](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/content_pieces_part1.csv), [part 2: /resources/comparison-guides/opsera-vs-jellyfish to /resources/white-papers/opsera-leading-the-charge-accelerating-secure-automated-and-cost-efficient-software-delivery](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/content_pieces_part2.csv).

## Google search tab

- [google_search_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_search_by_month.csv): Google search tab, by month. Source: Search Console. A lower average spot is better. 7 rows.
- [google_search_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_search_by_week.csv): Google search tab, by week. Source: Search Console. A lower average spot is better. 30 rows.
- [google_top_searches.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_top_searches.csv): The searches bringing the most Google clicks, 2026-04-01 to 2026-10-25. Source: Search Console. Google hides rare searches. 600 rows.
- [google_rankings_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_rankings_by_week.csv): Average spot on Google, Monday-to-Sunday weeks, for the homepage, the 8 product pages and the top 20 blogs and resources by visits since 2026-09-30. 1 is the top. Source: Google Search Console, up to 2026-10-25. 458 rows.
- [google_rankings_top_searches.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_rankings_top_searches.csv): The top 10 searches for each key page, 2026-07-29 to 2026-10-25. Source: Google Search Console. 286 rows.

## AEO tab: visits from AI tools

- [aeo_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_by_month.csv): AEO tab: visits from each AI tool and what came next, by month. Sources: Google Analytics, HubSpot. 30 rows.
- [aeo_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_by_week.csv): AEO tab: visits from each AI tool and what came next, by week. Sources: Google Analytics, HubSpot. 102 rows.

## LinkedIn brand tab (Opsera company page)

Paid means sponsored posts. LinkedIn's own sheets disagree on reposts, so we leave them out.

- [linkedin_brand_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_by_month.csv): LinkedIn brand tab (Opsera company page), by month. Source: LinkedIn exports, dates in UTC. 4 rows.
- [linkedin_brand_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_by_week.csv): LinkedIn brand tab (Opsera company page), by week. Source: LinkedIn exports, dates in UTC. 17 rows.
- [linkedin_brand_posts.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_posts.csv): Each Opsera company page post. Source: LinkedIn exports. 60 rows.

## LinkedIn exec tab (Kumar Chivukula)

- [linkedin_exec_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_by_month.csv): LinkedIn exec tab (Kumar Chivukula's profile), by month. Source: LinkedIn exports, dates in UTC. 4 rows.
- [linkedin_exec_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_by_week.csv): LinkedIn exec tab (Kumar Chivukula's profile), by week. Source: LinkedIn exports, dates in UTC. 18 rows.
- [linkedin_exec_exports.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_exports.csv): Each LinkedIn export of Kumar's profile as LinkedIn gave it. People reached doesn't add up across days. Source: LinkedIn exports. 4 rows.
- [linkedin_exec_post_list.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_post_list.csv): Each of Kumar's own LinkedIn posts since 1 Jul 2026 with reactions and comments. Source: his public profile, read with Apify. 27 rows.
- [linkedin_exec_posts_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_posts_by_month.csv): Kumar's own posts and reposts by month (UTC), 2 separate counts. Source: Kumar's public LinkedIn profile, read with Apify, checked 2026-10-27. 4 rows.

## LinkedIn visits to opsera.ai

Company page means links tagged utm_campaign=brand-page. Kumar means utm_source=linkedin with utm_campaign=kumar. Untagged is everything else from LinkedIn. We never add the 3 together. The estimate is a best guess, kept apart from the tagged numbers.

- [linkedin_visits_to_site_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_visits_to_site_by_month.csv): Visits to opsera.ai from LinkedIn: company page links, Kumar's links and untagged, by month. Source: Google Analytics. 21 rows.
- [linkedin_visits_to_site_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_visits_to_site_by_week.csv): Visits to opsera.ai from LinkedIn: company page links, Kumar's links and untagged, by week. Source: Google Analytics. 93 rows.
- [linkedin_untagged_estimate_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_untagged_estimate_by_month.csv): Best guess at who sent the untagged LinkedIn visits, by month. Source: Google Analytics matched to LinkedIn posts found with Apify. 6 rows.
- [linkedin_untagged_estimate_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_untagged_estimate_by_week.csv): Best guess at who sent the untagged LinkedIn visits, by week. Source: Google Analytics matched to LinkedIn posts found with Apify. 27 rows.

## YouTube tab

We never add Shorts and long videos together.

- [youtube_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_by_month.csv): YouTube tab, by month. Source: YouTube Analytics. 7 rows.
- [youtube_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_by_week.csv): YouTube tab, by week. Source: YouTube Analytics. 30 rows.
- [youtube_videos.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_videos.csv): Each video's views and watch time, 2026-04-01 to 2026-10-24. Source: YouTube Analytics. 199 rows.

## Pipeline tab

Marketing sourced and influenced pipeline from Salesforce exports (counts and totals only), and campaign-influenced meetings. Updated when new exports arrive, not on Mondays.

- [marketing_pipeline_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_by_month.csv): Marketing sourced (an estimate: it rests on Primary Campaign Source) and influenced pipeline, and deals with no contact linked as their own group (not sales), (open and won) by month, and the outside booking agency (DoGood, CrestingWave) on its own. Sourced: the Primary Campaign Source is a marketing campaign. Influenced: not sourced, but another campaign on the deal is. A campaign counts only if the person joined it within 90 days before the deal; 15 deals have no known join date and still count. SDR and AE outreach count as sales. Undercounted: 80% of opportunities have no contact attached. Source: Salesforce opportunities created 2026-05-08 to 2026-10-23, exported 2026-10-27, 2026-10-28. 6 rows.
- [marketing_pipeline_campaigns.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_campaigns.csv): The campaign behind each marketing sourced or influenced deal, 1 campaign per deal. Source: Salesforce opportunities created 2026-05-08 to 2026-10-23, exported 2026-10-27, 2026-10-28. 14 rows.
- [marketing_pipeline_meetings.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_meetings.csv): Campaign-influenced meetings: people with a meeting since 1 Apr 2026 who joined a marketing campaign on or before it, each counted once. Source: Salesforce campaign members, exported 2026-10-27. 7 rows.
- [deals_one_line_each.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/deals_one_line_each.csv): How each marketing deal came in: 1 line per deal, open or won, with no company or person. Source: HubSpot. The product comes from words in the deal name. 5 rows.

## Team metrics tab

Each person's metrics. The baseline is the July to September 2026 monthly average. "To set" means nobody has set a goal yet, so don't invent one. "Metrics coming" means the person hasn't sent their metrics yet.

- [team_metrics.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/team_metrics.csv): Team metrics tab: each person's metrics, with the baseline (July to September 2026 monthly average), this month so far and the goal. 15 rows.

## GTM calendar markers

The small diamonds under dated charts. Each is a launch, event or piece of content on its ship date. Use them to see what was going on when a number moved, not as proof one caused the other.

- [gtm_calendar.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/gtm_calendar.csv): Marketing launches, events and content from the GTM calendar, by ship date. The charts mark these dates. Source: Opsera GTM calendar in Notion, ship dates, pulled 2026-10-28. 26 rows.

## Before: Kahoots and Before: Infrasity tabs

These match the agencies' own reports exactly.

- [kahoots_monthly_as_reported.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/kahoots_monthly_as_reported.csv): What Kahoots reported by month, July to September 2026, from the old opsera.ai 2025 Google Analytics account. 3 rows.
- [kahoots_quarter_as_reported.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/kahoots_quarter_as_reported.csv): What Kahoots reported for Q2 and Q3 2026. 5 rows.
- [infrasity_monthly_as_reported.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/infrasity_monthly_as_reported.csv): What Infrasity reported by month, July to September 2026. 3 rows.
