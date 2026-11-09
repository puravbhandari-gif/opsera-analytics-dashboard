# To do

The dashboard's To do link shows this list. Tick an item with [x] when it's done, and add new ones as they come up.

## Website and marketing

- [ ] Update the pages on page 2 of Google, starting with the CI/CD pipeline blog (spot 11 for "ci/cd", 27,000 searches a month).
- [ ] Cursor article: add a next step and a demo button, and find out why its Google clicks fell from 469 in August to 195 in September.
- [ ] Write short answer pages for the AI questions we're missing on ("what is DevOps orchestration", "what is a software factory").
- [ ] Pause or redirect the LinkedIn Gartner ad.
- [ ] Copado page: add a switching section and a demo button.
- [ ] Fix blogs showing up twice on Google, with and without "/" at the end.
- [ ] Waiting on David and Yusra: HubSpot bot filtering, and connecting Luma.
- [ ] Fix Notion permission so I can create the read-only connection.
- [ ] Every Monday: ask Claude Code to write the Summary takeaways.
- [ ] Check with David why the GitHub Universe happy hour form shows 7 submits but only 2 in HubSpot.
- [ ] Fix the broken Salesforce blog link (/blog/why-salesforce-orgs-need-a-headless-devops-platform), which both Opsera and Kumar posted. It needs a redirect on the website.
- [ ] Tag Kumar's "Visit my website" button.
- [ ] Add "How did you hear about us" to the demo form (David).
- [ ] Add redirects for old links now showing Page not found. Each address, then the live page it should go to (checked 28 Oct 2026):
  - /resources/whitepapers to /resources
  - /resources/guides to /resources
  - /resources/blog to /blog
  - /resources/reports to /resources
  - /resources/customer-stories to /customer-stories
  - /blog/what-is-deployment-frequency to /knowledge-base/core-flow-metrics/deployment-frequency-a-clear-window-into-your-software-delivery-engine
  - /blog/ai-coding-impact-2026-benchmark-report to /resources/report/ai-coding-impact-2026-benchmark-report
  - /resources/report/ai-coding-impact-2025-benchmark-report to /resources/report/ai-coding-impact-2026-benchmark-report (the newest edition)
  - /resources/ai-coding-impact-benchmark-2026 to /resources/report/ai-coding-impact-2026-benchmark-report
  - /resources/state-of-ai-in-software-delivery-2025 to /resources/report/ai-coding-impact-2026-benchmark-report (the current AI report; or /newsroom/new-opsera-report-reveals-how-ai-is-transforming-software-delivery-and-driving-business-outcomes, the 2025 report's announcement)
  - /blog/dora-vs-space-metrics to /blog/dora-vs-space-metrics-key-differences-use-cases-and-when-to-use-each-framework
  - /knowledge-base/quality-risk/mean-time-to-restore-mttr-a-practical-guide-for-engineering-and-technology-leaders to /knowledge-base/core-reliability-metrics/mean-time-to-restore-mttr-a-practical-guide-for-engineering-and-technology-leaders

## Dashboard

- [ ] Influenced vs sourced pipeline, after syncing with David.
- [ ] All pipeline: sourced, influenced and sales only.
- [ ] Confirm with David: SDR outreach campaigns count as marketing or sales.
- [ ] Ask David for event campaign members with meeting set dates, and campaign members with first associated dates.
- [ ] Talk to Grover about fixing the Salesforce rule for Primary Campaign Source.
- [ ] Update Kumar's LinkedIn export every 2 weeks.
- [ ] Decide the website visits goal: all visits or without robots.
- [ ] Team members' metrics, as they come in.
- [ ] Business questions check, after the team replies.
- [ ] Ask our PR agencies for their coverage lists since 1 Jul 2026, save them in Desktop/Data/pr-agency, then ask Claude Code to add the PR agency list.
- [ ] When SamsonPR updates their tracker: ask Claude Code to "read SamsonPR's tracker". It saves it to Desktop/Data/pr-agency as SamsonPR-tracker-<date>.xlsx and runs `.venv/bin/python scripts/fetch_pr_media.py --agency`, which refreshes Placed by, Readership and the open and missed opportunities.
- [ ] When new blogs go up: ask Claude Code to tag each one with a type in data/blog_types.json. Untagged blogs show as "Not tagged yet" on the Content tab.
- [ ] Add publish dates to the guide pages (knowledge base and comparison guides), so they show in "Published this quarter".
- [ ] When Kumar's newsletter launches, add subscribers, opens and clicks per issue to the dashboard.
- [ ] Newsroom has no press release since 5 May; add the newer ones, including the 10 Jun 2026 VIBEshift release ("Opsera Launches VIBEshift" on PR Newswire).
- [ ] Every month: ask Claude Code to refresh Ahrefs for PR.
- [ ] When Infrasity sends a new growth report: save it to Desktop/Data/infrasity and ask Claude Code to check its claims and update the Infrasity section of the SEO and AEO view.
- [ ] SEO and AEO view covers 1 Jan to 31 Oct 2026. To extend it, change END in scripts/fetch_seo_aeo.py, run it on this Mac, and ask Claude Code to rewrite the 3 product lines in data/seo_aeo_lines.json.
- [x] Personal views: saved links per person.
- [x] GTM calendar markers on every dated chart, from Notion, with an on/off switch and a filter by type.
- [x] Google Ads on Customer journey, under the Paid ads funnel: spend, clicks, visits and cost per demo request by campaign.
- [x] Google rankings on Google search: average position week by week for key pages, and their top searches.
- [x] Events tab after Content: sign-ups, attended, event page form fills and meetings afterwards, 1 row per event.
- [x] Campaigns tab: visits, engaged visits, form fills, email sends, opens and clicks, and deals, 1 row per campaign.
- [x] Content scorecard tab.
- [x] Download button on every table.
- [x] Monday Slack post with the top numbers and the dashboard link, in #core-marketing-team.
- [ ] When David sends a new "DG-Demo Requests" export: save it to Desktop/Data/salesforce-exports and run `.venv/bin/python scripts/build_demo_requests.py`. It has X-Factor since the 5 Nov export.
