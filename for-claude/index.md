# Opsera website analytics, in plain text

The data behind the dashboard at https://puravbhandari-gif.github.io/opsera-analytics-dashboard/, written for AI assistants such as Claude.
Every number here also appears on the dashboard. We rebuild these files every time the dashboard is published: new numbers every Monday morning, India time, and any change in between. Google Analytics numbers pulled 2026-11-25.

## How to answer questions

- Read this guide first, then open only the files a question needs. Every file is a small CSV with a header row.
- Weeks run Monday to Sunday. Months are calendar months. `period_not_finished` is "yes" for a week or month still under way.
- Google Analytics and HubSpot dates follow US Pacific time. LinkedIn exports use UTC.
- Never add numbers from different sources together (for example Google Analytics visits and Search Console clicks). Each file and column says its source.
- "Without email robots" leaves out visits by email link checkers: visits with no engagement landing on email subscription pages (/hs/preferences-center), from Cupertino, Palo Alto, Garner or Sunnyvale, from Safari on a Mac desktop, or from the newsletter (utm_source dg_newsletter). All visits stays as Google Analytics counts it. Content visits also leave out the newsletter's visits with no engagement.
- "Visits" are Google Analytics sessions. "Engaged visits" are visits where someone stayed 10+ seconds, saw 2+ pages or filled a form. They leave out most email robots.
- Form fills count the HubSpot form event in Google Analytics. We leave out job application forms everywhere.
- Asset downloads are form fills on pages under /resources/report/, /resources/white-papers/, /resources/ebooks/ or /resources/comparison-guides/. They're part of "other forms".
- Deals exist as weekly and monthly totals, and as 1 line per marketing deal in deals_one_line_each.csv, without company or person names. Closed Lost deals stay out, and there are no daily deal numbers.
- When the dashboard compares periods, it compares the last full week with the week before, or this month so far with the same days of last month.
- A page in the page files is its address on opsera.ai, so `/pricing` is https://opsera.ai/pricing. Page titles are in the page_titles files.
- We split page and page title files by part of the site: blog, resources, knowledge base and other. Big ones also split by quarter, month or week, as the file name says.
- Questions about a campaign: use the campaign files (the utm_campaign in Google Analytics). Search Console counts Google clicks by page, so campaigns don't have them.
- Questions about a channel: use customer_journey_funnel (journey channels) or visit_sources (Google Analytics channel groups).
- If a question needs something these files don't have, say so instead of guessing.

## Date ranges

- Google Analytics and HubSpot: 2026-04-01 to 2026-11-23.
- Search Console (Google search): 2026-04-01 to 2026-11-23. It runs about 2 days behind.
- LinkedIn company page: 2026-07-01 to 2026-11-22. LinkedIn Kumar: 2026-07-01 to 2026-11-24, the last day still being counted when exported.
- YouTube: 2026-04-01 to 2026-11-21.
- Kahoots and Infrasity: July to September 2026, as they reported it.

## Exec view (Marketing at a glance)

The front page. Its cards take their numbers from the files below: marketing pipeline from marketing_pipeline_by_month (the only place sourced and influenced are added together), demo requests from leads, meetings with marketing contacts from customer_journey_summary, website visitors (visits without email robots) from website_visits, content published from content_published and PR placements from pr_coverage. Each card shows the fiscal quarter so far against the quarter before: the whole quarter, or the same days while this one isn't over.

- [content_published.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/content_published.csv): Exec view, content published: each blog, report, video and other piece published since 2026-07-01, checked 2026-11-24. Sources: Contentful, the opsera.ai sitemap and YouTube. 71 rows.

## Takeaways tab

The Going well, Needs attention and Do this week boxes, and one card per area. Claude Code writes the lines each Monday from the numbers; every line is checked against them.

- [takeaways_boxes.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/takeaways_boxes.csv): Takeaways tab: the Going well, Needs attention and Do this week lines for each view, written 2026-11-25. Sources: as each card says. 22 rows.
- [takeaways_cards.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/takeaways_cards.csv): Takeaways tab: one card per area with its main number, the period before, why it matters and what to do. Blank means nothing notable. 48 rows.

## Hub and spoke campaigns tab

- [hub_campaigns.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/hub_campaigns.csv): Hub and spoke campaigns tab: each campaign's hub piece and its spokes, with the number the tab shows. Sources: as the tab says for each campaign. 40 rows.

## PR and media tab

Articles about Opsera, Catapult's quarterly report, open media opportunities and share of voice. Never add news mentions to website numbers.

- [pr_catapult_report.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pr_catapult_report.csv): PR and media tab: Catapult's report for 1 Aug to 31 Oct 2026, as they reported it. 6 rows.
- [pr_coverage.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pr_coverage.csv): PR and media tab: each article since 2026-07-01, checked 2026-11-24. "To review" means not confirmed yet. Visits: Google Analytics. Domain rating: Ahrefs. 87 rows.
- [pr_opportunities.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pr_opportunities.csv): PR and media tab: open media opportunities from SamsonPR's tracker, read 2026-11-06. 7 rows.
- [pr_share_of_voice.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pr_share_of_voice.csv): PR and media tab: news mentions of Opsera and 5 competitors by fiscal quarter, from 2026-07-01. Source: Google News, checked 2026-11-24. 18 rows.

## SEO and AEO view

Google search and AI tool visits for each product (overall, Forge and Insights), from January 2026.

- [seo_aeo_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/seo_aeo_by_month.csv): SEO and AEO view: each product by month. Sources: Search Console for clicks, Google Analytics for AI visits, 2026-01-01 to 2026-10-31. 30 rows.
- [seo_aeo_keywords.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/seo_aeo_keywords.csv): SEO and AEO view: top searches for each product. Source: Search Console. 30 rows.
- [seo_aeo_top_pages.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/seo_aeo_top_pages.csv): SEO and AEO view: top pages for each product. Sources: Search Console for clicks, Google Analytics for AI visits, 2026-01-01 to 2026-10-31. 30 rows.
- [seo_aeo_tracked_pages.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/seo_aeo_tracked_pages.csv): SEO and AEO view: Google spot for tracked pages, first week against week of 2026-10-26. Source: Search Console. 46 rows.

## Customer journey tab

How marketing turns website visits into demo requests, meetings and deals. The funnel has 6 steps. Google Analytics counts visits, demo page views and demo form fills. HubSpot counts new contacts, meetings and deals. A contact is someone who first filled in the demo form. Meetings and deals count only after sign-up, never with existing customers. A later step can be bigger than the step before because the 2 tools count differently. For Google search, every step ends on Search Console's last day, and the first 2 columns are Search Console. "All channels" visits match the Website visits tab.

- [customer_journey_funnel_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_funnel_by_month.csv): The funnel for each channel, by month. Sources: Search Console for the 2 Google columns, Google Analytics from visits to demo form, HubSpot from contacts to deals. 72 rows.
- [customer_journey_funnel_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_funnel_by_week.csv): The funnel for each channel, by week. Sources: Search Console for the 2 Google columns, Google Analytics from visits to demo form, HubSpot from contacts to deals. 315 rows.
- [customer_journey_summary_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_summary_by_month.csv): Customer journey tab, top numbers, by month. Sources: Google Analytics (demo requests), HubSpot (meetings and deals). 8 rows.
- [customer_journey_summary_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/customer_journey_summary_by_week.csv): Customer journey tab, top numbers, by week. Sources: Google Analytics (demo requests), HubSpot (meetings and deals). 35 rows.

## Website visits tab

- [website_visits_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/website_visits_by_month.csv): Website visits tab, by month. Average engagement time is the seconds a page was in front of people, over all visits (robots included). Source: Google Analytics. 8 rows.
- [website_visits_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/website_visits_by_week.csv): Website visits tab, by week. Average engagement time is the seconds a page was in front of people, over all visits (robots included). Source: Google Analytics. 35 rows.
- [visit_sources_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/visit_sources_by_month.csv): Where visits came from (Google Analytics channel groups), by month. Source: Google Analytics. 82 rows.
- [visit_sources_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/visit_sources_by_week.csv): Where visits came from (Google Analytics channel groups), by week. Source: Google Analytics. 299 rows.
- [button_clicks.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/button_clicks.csv): Website visits tab: clicks on Book a demo and other buttons, by day and page. Source: Google Analytics. 329 rows.
- heat_map_by_day, split to stay small: Website visits tab, heat map numbers: each day covers the 24 hours before the pull. Source: Microsoft Clarity. Parts: [2026-11-09, part 1](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-09_part1.csv), [2026-11-09, part 2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-09_part2.csv), [2026-11-16, part 1](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-16_part1.csv), [2026-11-16, part 2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-16_part2.csv), [2026-11-16, part 3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-16_part3.csv), [2026-11-23](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/heat_map_by_day_2026-11-23.csv).
- [who_visits.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/who_visits.csv): Website visits tab, Who visits: 1206 companies and 1404 people Warmly matched to visits, 2026-08-26 to 2026-11-24. Counts only. Source: HubSpot (Warmly). 20 rows.

## Leads tab

Demo requests are form fills on /demo. Contact forms are on /contact. The Gartner offer is /gartner-symposium/free-modernization. Event sign-ups are /events/ pages, /gartner-symposium and /github-universe-happy-hour. Everything else is other forms. Before October, the old site sent some homepage and contact form fills only to Google, so earlier months look low. Luma event sign-ups don't show here.

- [leads_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/leads_by_month.csv): Leads tab: form fills by kind of form, by month. Source: Google Analytics (HubSpot form event). 8 rows.
- [leads_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/leads_by_week.csv): Leads tab: form fills by kind of form, by week. Source: Google Analytics (HubSpot form event). 35 rows.
- [leads_demo_by_product.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/leads_demo_by_product.csv): Leads tab: demo requests by the product chosen on the form, by day. Source: Google Analytics (HubSpot form event). 60 rows.

## Events tab

Each webinar, roundtable and event since 1 Apr, and the HubSpot sign-up lists, each on its own.

- [events_one_row_each.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/events_one_row_each.csv): Each webinar, roundtable and event since 1 Apr 2026. Sign-ups, attended and meetings come from HubSpot; event page form fills from Google Analytics. Never add the two together. Blank means no data. 8 rows.
- [hubspot_event_lists.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/hubspot_event_lists.csv): Event sign-up lists in HubSpot, each on its own (never added together). Source: HubSpot. 4 rows.
- [luma_flutter.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/luma_flutter.csv): Events tab: Flutter 2026 guests on Luma by source tag, exported 2026-11-09. Valentina reported 509 registered. Source: Luma. 14 rows.

## Campaigns tab

Each campaign's link-tag visits and HubSpot emails and deals (the campaigns file below the Look up section), and Google Ads by campaign.

- [google_ads_by_campaign.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_ads_by_campaign.csv): Google Ads spend and ad clicks (counted by Google Ads) with visits and demo requests (counted by Google Analytics), per campaign per month. Brand search visits and demo requests from 16 Jun 2026 are too low because of a tracking problem. Source: Google Analytics, opsera.ai 2026, linked to Google Ads. 12 rows.
- [hubspot_marketing_emails.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/hubspot_marketing_emails.csv): HubSpot marketing emails since 1 Apr 2026 with sends, opens and clicks. The subject line shows; emails aimed at named target accounts are left out. Source: HubSpot. 267 rows.

## Pages, campaigns and assets (the Look up tab)

Visits count people who landed on the page from outside the site. Page files list a page in a period only when it had a visit, form fill or Google click.

- pages_by_month_blog, split to stay small: Pages under /blog/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-09.csv), [2026-10](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-10.csv), [2026-11](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-11.csv), [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_blog_2026-Q2.csv).
- [pages_by_month_knowledge_base.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_knowledge_base.csv): Pages under /knowledge-base/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. 318 rows.
- [pages_by_month_main.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_main.csv): Main pages 1 level deep (the homepage, /demo, /pricing and the like) by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. 512 rows.
- pages_by_month_other, split to stay small: Pages in other sections such as /newsroom/ and /changelog/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-08.csv), [2026-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-09.csv), [2026-10](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-10.csv), [2026-11](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-11.csv), [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_other_2026-Q2.csv).
- pages_by_month_resources, split to stay small: Pages under /resources/ by month. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_month_resources_2026-Q4.csv).
- pages_by_week_blog, split to stay small: Pages under /blog/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-05.csv), [2026-06-01](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-01.csv), [2026-06-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-08.csv), [2026-06-15](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-15.csv), [2026-06-22](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-22.csv), [2026-06-29](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-06-29.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-08.csv), [2026-09-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-07.csv), [2026-09-14](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-14.csv), [2026-09-21](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-21.csv), [2026-09-28](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-09-28.csv), [2026-10](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-10.csv), [2026-11-02](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-11-02.csv), [2026-11-09](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-11-09.csv), [2026-11-16](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-11-16.csv), [2026-11-23](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_blog_2026-11-23.csv).
- pages_by_week_knowledge_base, split to stay small: Pages under /knowledge-base/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_knowledge_base_2026-Q4.csv).
- pages_by_week_main, split to stay small: Main pages 1 level deep (the homepage, /demo, /pricing and the like) by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_main_2026-Q4.csv).
- pages_by_week_other, split to stay small: Pages in other sections such as /newsroom/ and /changelog/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-04](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-04.csv), [2026-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-05.csv), [2026-06-01](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-01.csv), [2026-06-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-08.csv), [2026-06-15](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-15.csv), [2026-06-22](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-22.csv), [2026-06-29](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-06-29.csv), [2026-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-07.csv), [2026-08](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-08.csv), [2026-09-07](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-07.csv), [2026-09-14](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-14.csv), [2026-09-21](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-21.csv), [2026-09-28](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-09-28.csv), [2026-10-05](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-05.csv), [2026-10-12](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-12.csv), [2026-10-19](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-19.csv), [2026-10-26](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-10-26.csv), [2026-11](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_other_2026-11.csv).
- pages_by_week_resources, split to stay small: Pages under /resources/ by week. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks. Parts: [2026-Q2](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-Q2.csv), [2026-Q3](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-Q3.csv), [2026-Q4](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pages_by_week_resources_2026-Q4.csv).
- [page_titles_blog.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_blog.csv): The title of each page: pages under /blog/. Source: Google Analytics. 297 rows.
- [page_titles_knowledge_base.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_knowledge_base.csv): The title of each page: pages under /knowledge-base/. Source: Google Analytics. 81 rows.
- [page_titles_main.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_main.csv): The title of each page: main pages 1 level deep (the homepage, /demo, /pricing and the like). Source: Google Analytics. 187 rows.
- page_titles_other, split to stay small: The title of each page: pages in other sections such as /newsroom/ and /changelog/. Source: Google Analytics. Parts: [part 1: /"/about/" to /wp-json/wp/v2/posts/8107](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_other_part1.csv), [part 2: /wp-json/wp/v2/posts/821 to /wp-json/wp/v2/resource/8544](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_other_part2.csv).
- [page_titles_resources.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/page_titles_resources.csv): The title of each page: pages under /resources/. Source: Google Analytics. 102 rows.
- [campaigns_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_by_month.csv): Every campaign (utm_campaign) with visits or form fills, by month. Source: Google Analytics. 301 rows.
- [campaigns_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_by_week.csv): Every campaign (utm_campaign) with visits or form fills, by week. Source: Google Analytics. 456 rows.
- [campaigns_since_1_apr.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/campaigns_since_1_apr.csv): Each campaign since 1 Apr 2026: visits, engaged visits and form fills from Google Analytics link tags (to 2026-11-23), emails and deals from HubSpot. Never add the two sources together. A deal belongs to the campaign its person first came in on. Target-account campaigns, sales outreach codes and spam sites are left out. 232 rows.

## Content tab

One row per blog post, report, white paper, eBook, guide (knowledge base article) and comparison page. content_pieces lists each piece with its type; its visits, form fills and Google clicks are in the page files above. A deal counts for a piece when the contact's first page or first form was that piece (see deals_one_line_each.csv).

- content_pieces, split to stay small: Content tab: each blog post, report, white paper, eBook, guide and comparison page with its type. Their numbers are in the page files. Parts: [part 1: /blog/10-must-have-salesforce-devops-tools-and-how-to-orchestrate-them-right to /knowledge-base/security-and-devsecops-metrics/time-to-mitigate-vulnerability-ttmv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/content_pieces_part1.csv), [part 2: /knowledge-base/security-and-devsecops-metrics/understanding-system-hardening-timelines-in-devsecops-environments to /resources/white-papers/tokenomics-the-currency-of-enterprise-ai](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/content_pieces_part2.csv).

## Google search tab

- [google_search_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_search_by_month.csv): Google search tab, by month. Source: Search Console. A lower average spot is better. 8 rows.
- [google_search_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_search_by_week.csv): Google search tab, by week. Source: Search Console. A lower average spot is better. 35 rows.
- [google_top_searches.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_top_searches.csv): The searches bringing the most Google clicks, 2026-04-01 to 2026-11-23. Source: Search Console. Google hides rare searches. 600 rows.
- [google_rankings_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_rankings_by_week.csv): Average spot on Google, Monday-to-Sunday weeks, for the homepage, the 8 product pages and the top 20 blogs and resources by visits since 2026-09-30. 1 is the top. Source: Google Search Console, up to 2026-11-23. 477 rows.
- [google_rankings_top_searches.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/google_rankings_top_searches.csv): The top 10 searches for each key page, 2026-08-27 to 2026-11-23. Source: Google Search Console. 290 rows.

## AEO tab: visits from AI tools

- [aeo_ai_answers.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_ai_answers.csv): AEO tab, AI visibility: whether ChatGPT and Google AI Mode name Opsera for 10 questions, checked daily 2026-10-26 to 2026-11-23. Source: Ahrefs Brand Radar. 20 rows.
- [aeo_ai_bots_by_day.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_ai_bots_by_day.csv): AEO tab: AI bots reading opsera.ai by day. Never add these to people visits. Source: Google Analytics, AI bots property. 219 rows.
- [aeo_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_by_month.csv): AEO tab: visits from each AI tool and what came next, by month. Sources: Google Analytics, HubSpot. 34 rows.
- [aeo_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/aeo_by_week.csv): AEO tab: visits from each AI tool and what came next, by week. Sources: Google Analytics, HubSpot. 111 rows.

## LinkedIn brand tab (Opsera company page)

Paid means sponsored posts. LinkedIn's own sheets disagree on reposts, so we leave them out.

- [linkedin_brand_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_by_month.csv): LinkedIn brand tab (Opsera company page), by month. Source: LinkedIn exports, dates in UTC. 5 rows.
- [linkedin_brand_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_by_week.csv): LinkedIn brand tab (Opsera company page), by week. Source: LinkedIn exports, dates in UTC. 21 rows.
- [linkedin_brand_posts.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_brand_posts.csv): Each Opsera company page post. Source: LinkedIn exports. 71 rows.

## LinkedIn exec tab (Kumar Chivukula)

- [linkedin_exec_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_by_month.csv): LinkedIn exec tab (Kumar Chivukula's profile), by month. Source: LinkedIn exports, dates in UTC. 5 rows.
- [linkedin_exec_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_by_week.csv): LinkedIn exec tab (Kumar Chivukula's profile), by week. Source: LinkedIn exports, dates in UTC. 22 rows.
- [linkedin_exec_exports.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_exports.csv): Each LinkedIn export of Kumar's profile as LinkedIn gave it. People reached doesn't add up across days. Source: LinkedIn exports. 9 rows.
- [linkedin_exec_post_list.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_post_list.csv): Each of Kumar's own LinkedIn posts since 1 Jul 2026 with reactions and comments. Source: his public profile, read with Apify. 31 rows.
- [linkedin_exec_posts_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_exec_posts_by_month.csv): Kumar's own posts and reposts by month (UTC), 2 separate counts. Source: Kumar's public LinkedIn profile, read with Apify, checked 2026-11-24. 5 rows.

## LinkedIn to website tab

From a LinkedIn post to the demo form, by account. Visits are matched to posts by the UTM tags on the post's link: utm_content brand-post (or utm_campaign brand-page, the profile button) is the brand page, utm_content kumar (or utm_campaign kumar) is Kumar, utm_content vishnu is other Opsera people, paid mediums are LinkedIn ads, and everything else is "LinkedIn, account unknown". Tagged links started on 27 Oct 2026 for the brand page and 17 Nov 2026 for Kumar. Product pages are the site menu's: /software-factory, /forge, /unified-insights, /agents, /agentic-devops, /salesforce-devops and /brickforge. Times seen and clicks come from LinkedIn, visits and steps from Google Analytics: never add them together, and never add the brand page and Kumar together. Brand page clicks are every click on a post; Kumar's are visits to links, only for his 3 latest posts.

- [linkedin_to_site_posts.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_to_site_posts.csv): LinkedIn to website tab: each brand page and Kumar post with times seen and clicks (LinkedIn) and the opsera.ai links in it with their tags (read with Apify). 83 rows.
- [linkedin_to_site_steps.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_to_site_steps.csv): LinkedIn to website tab: visits from LinkedIn that opened a product page, /demo and sent the demo form, by day, account and tag. Source: Google Analytics. 59 rows.
- [linkedin_to_site_visits.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_to_site_visits.csv): LinkedIn to website tab: visits from LinkedIn by day, account, tag (campaign / content) and landing page, 2026-07-27 to 2026-11-24. Source: Google Analytics. 547 rows.

## LinkedIn visits to opsera.ai

The same rule as the LinkedIn to website tab: utm_content brand-post (or utm_campaign brand-page, the profile button) is the company page, utm_content kumar (or utm_campaign kumar) is Kumar, utm_content vishnu is other Opsera people, paid mediums are LinkedIn ads, and everything else is "LinkedIn, account unknown". We never add the groups together. The estimate is a best guess, kept apart from the tagged numbers.

- [linkedin_visits_to_site_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_visits_to_site_by_month.csv): Visits to opsera.ai from LinkedIn by who sent them: company page, Kumar, other Opsera people, LinkedIn ads and account unknown, by month. Source: Google Analytics. 40 rows.
- [linkedin_visits_to_site_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_visits_to_site_by_week.csv): Visits to opsera.ai from LinkedIn by who sent them: company page, Kumar, other Opsera people, LinkedIn ads and account unknown, by week. Source: Google Analytics. 175 rows.
- [linkedin_untagged_estimate_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_untagged_estimate_by_month.csv): Best guess at who sent the untagged LinkedIn visits, by month. Source: Google Analytics matched to LinkedIn posts found with Apify. 9 rows.
- [linkedin_untagged_estimate_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/linkedin_untagged_estimate_by_week.csv): Best guess at who sent the untagged LinkedIn visits, by week. Source: Google Analytics matched to LinkedIn posts found with Apify. 39 rows.

## YouTube tab

We never add Shorts and long videos together.

- [youtube_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_by_month.csv): YouTube tab, by month. Source: YouTube Analytics. 8 rows.
- [youtube_by_week.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_by_week.csv): YouTube tab, by week. Source: YouTube Analytics. 34 rows.
- [youtube_videos.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/youtube_videos.csv): Each video's views and watch time, 2026-04-01 to 2026-11-21. Source: YouTube Analytics. 200 rows.

## Pipeline tab

Marketing sourced and influenced pipeline: Salesforce deals as synced to HubSpot, counts and totals only. Older campaign touches, past meetings and partner flags come from Salesforce exports frozen on 22 Nov 2026. Deals with a partner listed count as influenced, never sourced. Fiscal quarters: Q1 is Feb to Apr, Q2 May to Jul, Q3 Aug to Oct, Q4 Nov to Jan.

- [marketing_pipeline_by_month.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_by_month.csv): Marketing sourced, influenced and booking agency pipeline by month, open, won and lost, with deals that have no contact linked as their own group (not sales). The booking agency (DoGood, CrestingWave) is shown on its own and isn't marketing. Sourced: the Primary Campaign Source is a marketing campaign. Influenced: not sourced, but another campaign on the deal is. Deals with a partner listed count as influenced, never sourced. A campaign counts only if the person joined it within 90 days before the deal. SDR and AE outreach count as sales. Still estimated: both rest on Salesforce's campaign fields, and the Primary Campaign Source rule isn't reliable until it's fixed in Salesforce. For 38 deals nobody knows when the person joined the campaign, so the 90-day rule can't be checked and they still count. 64% of deals have no contact linked, so marketing's share is likely undercounted. Source: Salesforce opportunities created 2026-01-05 to 2026-11-20, exported 2026-10-27, 2026-11-02, 2026-11-09, 2026-11-17, 2026-11-22, 2026-11-23. 8 rows.
- [marketing_pipeline_campaigns.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_campaigns.csv): The campaign behind each marketing sourced or influenced deal, 1 campaign per deal. Source: Salesforce opportunities created 2026-01-05 to 2026-11-20, exported 2026-10-27, 2026-11-02, 2026-11-09, 2026-11-17, 2026-11-22, 2026-11-23. 32 rows.
- [marketing_pipeline_meetings.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/marketing_pipeline_meetings.csv): Campaign-influenced meetings: people with a meeting since 1 Apr 2026 who joined a marketing campaign on or before it, each counted once. Source: Salesforce campaign members, exported 2026-11-17. 7 rows.
- [pipeline_demo_request_funnel.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pipeline_demo_request_funnel.csv): Pipeline tab, from demo request to meeting to deal: each demo request day by status, 2026-04-01 to 2026-11-22. Source: Salesforce campaign DG-Demo Requests as synced to HubSpot. 45 rows.
- [pipeline_event_campaign_members.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pipeline_event_campaign_members.csv): Pipeline tab: event campaign members in Salesforce by status. Source: HubSpot's copy of Salesforce campaign members. 4 rows.
- [pipeline_open_deals_by_stage.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/pipeline_open_deals_by_stage.csv): Pipeline tab: open deals created since 2026-04-01 by stage, as of 2026-11-23. Age is days since the deal was created. Source: Salesforce deals as synced to HubSpot. 7 rows.
- [deals_one_line_each.csv](https://puravbhandari-gif.github.io/opsera-analytics-dashboard/for-claude/deals_one_line_each.csv): How each marketing deal came in: 1 line per deal, open, won or lost, with no company or person. Source: HubSpot. The product comes from words in the deal name. 6 rows.

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
