# How the dashboard updates

Link: https://puravbhandari-gif.github.io/opsera-analytics-dashboard/

## Every Monday, by itself

Every Monday at about 8:00 in the morning India time, GitHub runs a small script for us. It:

1. Signs in to Google with our read-only robot account (`dashboard-reader@opsera-analytics-dashboard.iam.gserviceaccount.com`).
2. Pulls our numbers from Search Console, Google Analytics "opsera.ai 2026" and YouTube, from 1 Sep 2026 up to yesterday. Leads start on 1 Oct 2026, because the old site sent some September forms only to Google and not to HubSpot.
3. Saves them in the `data` folder and republishes the page.

GitHub sometimes starts scheduled jobs up to an hour late, so give it until about 9:30.

If a number doesn't add up, the script stops instead of guessing. When that happens, the page keeps last week's numbers and GitHub sends you an email saying the run failed. Open the failed run to see the reason, which starts with "STOPPED:".

## Running it by hand, any time

1. Go to https://github.com/puravbhandari-gif/opsera-analytics-dashboard/actions
2. Click **Update numbers and publish** on the left.
3. Click the **Run workflow** button on the right, then the green **Run workflow** button.
4. Wait about two minutes. When the dot turns into a green tick, the page is updated. Reload it to see the new numbers.

## Things that never update

The Kahoots and Infrasity tabs are kept exactly as reported. Their numbers live in `data/kahoots_monthly.json`, `data/kahoots_quarter.json` and `data/infrasity_monthly.json`, and the script never touches them.

## Week by week or month by month

The switch at the top of the page changes every tab at once. Week by week compares the last full Monday-to-Sunday week with the week before. Month by month compares this month so far with the whole of last month. The Kahoots and Infrasity tabs were reported by month, so they always compare September with August.

## The LinkedIn tabs

The LinkedIn brand and LinkedIn exec tabs don't update on Mondays. Their numbers come from exports you download from LinkedIn yourself. The original files stay private in the Data folder on your Desktop and are never put in this public repo. Only `data/linkedin.json`, which holds the numbers the tabs show, is published.

To refresh them, download new exports from LinkedIn and ask Claude to update the LinkedIn tabs. Claude moves the files into Desktop/Data and runs `scripts/convert_linkedin.py`, which checks that the numbers add up and stops if they don't. Then Claude shows you the result before publishing.

## The YouTube tab

The Monday update also pulls the Opsera YouTube channel's numbers from YouTube's own APIs. It uses a read-only login that marketing@opsera.io gave once. That login is stored as a GitHub secret called `YOUTUBE_TOKEN`, and a copy is kept on Purav's Mac in `~/.config/opsera-dashboard/`.

The login stops working if someone removes the app's access for marketing@opsera.io, or if that account's password changes. When that happens, the Monday run fails with a "STOPPED" or "invalid_grant" message, and the page keeps last week's numbers. To fix it, ask Claude to run the YouTube sign-in again (`scripts/youtube_login.py`), sign in as marketing@opsera.io, pick the Opsera channel, and store the new login in the `YOUTUBE_TOKEN` secret.

## The Google key

The robot account's key is stored as a GitHub secret called `GOOGLE_SA_KEY`, under Settings > Secrets and variables > Actions. Nobody can read it there, not even you, and it isn't in the code. If it ever needs replacing, make a new key in Google Cloud for `dashboard-reader`, then paste it into that secret with **Update**. On Purav's Mac there's also a copy in `~/.config/opsera-dashboard/`, outside this folder.

## If Monday updates stop

GitHub pauses scheduled jobs if a repo has no activity for 60 days. The weekly number updates count as activity, so this shouldn't happen. If it does, GitHub shows an **Enable workflow** button on the Actions page.
