# How the dashboard updates

Link: https://puravbhandari-gif.github.io/opsera-analytics-dashboard/

## Every Monday, by itself

Every Monday at about 8:00 in the morning India time, GitHub runs a small script for us. It:

1. Signs in to Google with our read-only robot account (`dashboard-reader@opsera-analytics-dashboard.iam.gserviceaccount.com`).
2. Pulls our numbers from Search Console and from Google Analytics "opsera.ai 2026", from 1 Oct 2026 up to yesterday.
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

## The LinkedIn tab

The LinkedIn tab doesn't update on Mondays. Its numbers come from exports you download from LinkedIn yourself. The original files stay private in the Data folder on your Desktop and are never put in this public repo. Only `data/linkedin.json`, which holds the numbers the tab shows, is published.

To refresh it, download new exports from LinkedIn and ask Claude to update the LinkedIn tab. Claude moves the files into Desktop/Data and runs `scripts/convert_linkedin.py`, which checks that the numbers add up and stops if they don't. Then Claude shows you the result before publishing.

## The Google key

The robot account's key is stored as a GitHub secret called `GOOGLE_SA_KEY`, under Settings > Secrets and variables > Actions. Nobody can read it there, not even you, and it isn't in the code. If it ever needs replacing, make a new key in Google Cloud for `dashboard-reader`, then paste it into that secret with **Update**. On Purav's Mac there's also a copy in `~/.config/opsera-dashboard/`, outside this folder.

## If Monday updates stop

GitHub pauses scheduled jobs if a repo has no activity for 60 days. The weekly number updates count as activity, so this shouldn't happen. If it does, GitHub shows an **Enable workflow** button on the Actions page.
