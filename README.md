# Inbox Assistant

A small tool that keeps your Gmail inbox tidy on its own.

It does three things:

1. **Makes a list of everyone who has ever emailed you**, with how many emails each sender sent.
2. **Sorts your emails into labels** (for example `finance`, `family`, `jobs`) using rules that you write.
3. **Moves old, unsorted emails to the Trash** (30 days or older, only emails that match none of your rules).

Nothing is ever deleted permanently. Trashed emails stay in Gmail's Trash for 30 days, and you can restore them from there.

---

## Read this first: safety

This tool moves emails to the Trash based on **your** rules. Your mailbox may hold things you can't afford to lose: bank letters, contracts, tickets, password resets, old photos sent to yourself.

- **Anything that is not covered by your rules is moved to the Trash after 30 days.**
- That is why you must write the rules file yourself, by hand, after looking at the list of senders (see [Step 3](#step-3-write-your-rules-gmail_rulesjson)). Nobody else knows which senders matter to you.
- When in doubt, put a sender into a category. A sender in any category is never trashed.
- Check your Gmail Trash now and then, especially in the first weeks.

---

## What you need

- A Gmail account
- A computer with **Python 3** (Linux or Mac; the scheduling part below is written for Linux)
- About 20 minutes for the first setup

---

## Step 1: Install

Open a terminal in this folder and run:

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Step 2: Get Gmail access (one time)

Google requires every program that reads your mail to have its own "key". You create it for free:

1. Go to <https://console.cloud.google.com/> and sign in with your Google account.
2. Create a new project (or pick an existing one). The name doesn't matter.
3. Search for **Gmail API** and click **Enable**.
4. Go to **APIs & Services → Credentials → Create credentials → OAuth client ID**.
   - If asked, set up the "consent screen" first: choose **External**, fill in an app name and your email, and add your own Gmail address as a **test user**.
   - Application type: **Desktop app**.
5. Click **Download JSON**.
6. Rename the downloaded file to **`client_secret.json`** and put it in this folder.

On the first run, a browser window opens and asks you to allow the app to access your Gmail. Because the app is only for you, Google may show a "this app isn't verified" warning. Choose **Advanced → Continue**.

> Google only shows the client secret **once**, when you create it. Download the JSON right away and keep a backup copy. If you lose it, create a new OAuth client (**Create credentials → OAuth client ID → Desktop app**).
>
> Your login is saved in a separate file, `token.json`, so you don't have to log in every time. It is created automatically on the first run. Never share it.

## Step 3: Write your rules (`gmail_rules.json`)

This is the most important step, and the one that takes the longest. Do it carefully.

### 3a. Get the list of senders

Run the script once so it can build the list:

```bash
python3 gmail-automation.py
```

The first thing it does is read your whole mailbox (this can take several minutes) and write **`senders_list.json`**: every sender address with the number of emails they sent you, for example:

```json
{
  "newsletter@shop.com": 204,
  "bank@mybank.com": 58,
  "mum@gmail.com": 12
}
```

If the script then says "gmail_rules.json not found", that's expected. Create the rules file in the next step and run it again.

### 3b. Create `gmail_rules.json`

Open `senders_list.json` and go through the senders one by one. Create a new file called `gmail_rules.json` in the same folder. Each **category** becomes a Gmail label, and each category contains a list of sender addresses:

```json
{
  "finance": [
    "bank@mybank.com",
    "invoices@electricity.com"
  ],
  "family": [
    "mum@gmail.com"
  ],
  "jobs": [
    "jobs-noreply@linkedin.com"
  ],
  "uncategorized_trash": [
    "newsletter@shop.com"
  ]
}
```

Rules to follow:

- The file must be valid JSON: every address in double quotes, commas between items, **no comma after the last item**, no extra text.
- The category name is used as the Gmail label name. Use simple lowercase words.
- Copy addresses exactly as they appear in `senders_list.json`.
- A sender must appear in **one** category only.
- Put the senders you **want to keep** in real categories (`finance`, `family`, `medical`, ...).
- Every category in the file, including a junk category like `uncategorized_trash`, only **labels** mail. The 30-day cleanup trashes only mail from senders that appear in **no** category. So a sender you never list is trashed after 30 days, and a sender you list is kept, whatever the category is called.
- Work through the list from the biggest counts downward. A few dozen senders usually cover most of your mail.

Tip: ask an AI assistant (or a friend) to help you turn `senders_list.json` into a first draft of categories, then **review it yourself** before saving. Never run on a draft you haven't read.

## Step 4: First run

```bash
python3 gmail-automation.py
```

What happens:

1. It logs in to Gmail (browser window the first time).
2. It loads `senders_list.json`, or builds it if it doesn't exist.
3. It creates one Gmail label per category and puts the labels on **all existing** emails from the listed senders.
4. It asks: *"Delete old uncategorized emails (older than 30 days)? (y/n)"*. Answer **n** the first time, open Gmail, and check that the labels look right. Run again and answer **y** when you're happy.

"Delete" here means **move to Trash**, not permanent deletion.

## Step 5: Run it automatically (cron)

After the first run you don't need to do anything by hand. A "cron job" runs `cron-job-weekly.py` on a schedule. Each run:

- puts labels on **new** emails from the senders in your rules, and
- moves emails older than 30 days that match no rule to the Trash.

It writes a log to `/tmp/gmail_automation.log`.

### Try it by hand first

```bash
cd ~/Documents/inbox-assistant-filter
python3 cron-job-weekly.py
```

If it finishes without errors, the scheduled job will work too.

### Turn on the scheduler

```bash
sudo systemctl start crond
sudo systemctl enable crond
```

This makes sure the scheduler is running and starts again after a reboot.

### Add the job

```bash
crontab -e
```

An editor opens. Add **one** of the lines below (change the folder path if yours is different):

| How often | Line to add |
|---|---|
| Every Sunday at 10:00 | `0 10 * * 0 cd /home/emilija/Documents/inbox-assistant-filter && python3 cron-job-weekly.py >> /tmp/gmail_automation.log 2>&1` |
| Every day at 10:00 | `0 10 * * * cd /home/emilija/Documents/inbox-assistant-filter && python3 cron-job-weekly.py >> /tmp/gmail_automation.log 2>&1` |
| First day of each month at 10:00 | `0 10 1 * * cd /home/emilija/Documents/inbox-assistant-filter && python3 cron-job-weekly.py >> /tmp/gmail_automation.log 2>&1` |

How to read the first five fields (`0 10 * * 0`):

```
minute  hour  day-of-month  month  day-of-week
  0      10        *          *        0        = Sunday 10:00
```

- Change `10` to another hour. It uses 24-hour time, so 10 PM is `22`.
- Day of week: `0` = Sunday, `1` = Monday, ... `6` = Saturday.
- `*` means "every".

Save and close the editor. Check that it was saved:

```bash
crontab -l
```

### Check that it works

```bash
sudo systemctl status crond      # is the scheduler running?
sudo journalctl -u crond -f      # watch scheduler activity live
cat /tmp/gmail_automation.log    # what the tool did on each run
```

Note: `/tmp` is cleared when the computer restarts. If you want to keep the log, use a different path such as `~/gmail_automation.log` in the cron line.

---

## Large mailboxes: the 100-email limit per run

By default, each run handles **at most 100 emails per sender** when labeling, and **at most 100 old emails** when cleaning up. Gmail returns results in pages, and the scripts only read the first page (`maxResults=100`). Anything beyond that is picked up by the next run, because emails that are already labeled no longer match the search.

For normal use this is fine: a sender rarely sends more than 100 emails in a week. It only matters for a big backlog. A sender with 500 old emails needs about 5 runs to be fully labeled.

### Want everything done in one run?

You can make the scripts keep reading pages until nothing is left. **Before you do, understand the cost:**

> **Every email that gets a label costs one separate Gmail API call.**
> Labeling 5,000 emails means 5,000 calls, plus one call per page of search results. Cleaning up 2,000 old emails means 2,000 more.
> Gmail limits how fast you may call the API. If you go too fast you get "429 / rate limit" errors, and the scripts hide those errors (the `except: pass` blocks), so some emails would be silently skipped until the next run.

So the more emails you have, the longer the run and the higher the chance of hitting the limit. Recommended approach:

1. **Do the big backlog once, by hand**, not from cron. Run `python3 cron-job-weekly.py` and watch it.
2. Keep the weekly cron job on the default 100 limit. It is light and safe.

### How to change the script

In `cron-job-weekly.py`, find `label_new_emails()`. Replace the single search call with a loop that follows the "next page" marker:

```python
page_token = None
while True:
    results = self.service.users().messages().list(
        userId='me',
        q=f'from:{sender} -label:{category}',
        maxResults=100,
        pageToken=page_token
    ).execute()

    for msg in results.get('messages', []):
        # ... the existing modify(...) code stays exactly as it is ...

    page_token = results.get('nextPageToken')
    if not page_token:
        break
```

Do the same in `delete_old_uncategorized()` for the cleanup, and in `apply_labels()` in `gmail-automation.py` for the first run.

To go easier on Gmail's rate limit, add a short pause after each labeled email, for example `time.sleep(0.1)` (and `import time` at the top). A pause of 0.1 seconds means about 10 emails per second, which stays well under the limit.

If it still fails with rate-limit errors, wait a few minutes and run it again. Emails already labeled are skipped, so nothing is done twice.

**Advanced option (fewer calls):** Gmail has `messages().batchModify`, which labels up to 1,000 emails in a single call instead of one call per email. It is much cheaper but needs a bigger code change: collect the message IDs first, then send them in groups of up to 1,000.

---

## What's fixed

These problems existed in the first version and are now fixed.

| Problem | What was wrong | What it does now |
|---|---|---|
| **Login overwrote your Google key** | The login was saved into `client_secret.json`, replacing the file you downloaded. A fresh file from Google then crashed the script. | The login is saved in its own file, **`token.json`**. `client_secret.json` is never changed. |
| **Cron failed without telling you** | If the login had expired, the weekly job carried on without access and reported "Done". | It stops, writes `AUTH FAILED` to the log and exits with an error. Fix: run `python3 gmail-automation.py` by hand once to log in again. |
| **Errors were hidden** | The weekly job ignored all errors (rate limits, "insufficient scopes"), so it said "Labeled 0 emails" while failing. | Every Gmail error is written to the log as `ERROR: ...`, and the job exits with an error code at the end. |
| **Delete failed with 403** | Permanent delete needs a bigger permission than the tool asks for. | Old emails now go to the **Trash** (recoverable for 30 days). |
| **Too many API calls** | The weekly job sent one API call per email. | It labels and trashes up to 1,000 emails in **one** call (`batchModify`). Much faster and far less likely to hit Gmail's rate limit. |
| **No way to preview** | You could only find out what was trashed afterwards. | Run with **`--dry-run`** (see below). |
| **Same login code in two places** | Both scripts had their own copy, and they had drifted apart. | One shared file, **`auth.py`**, used by both. |
| **Broken Trash filter** | The old search `-label:[Gmail]/Trash` is not valid Gmail search. | Uses `-in:trash`. |
| **Emails labeled twice** | A sender listed in two categories got both labels. | The weekly job only touches emails that have **no label** (`has:nouserlabels`). |

### Preview before anything is changed: `--dry-run`

```bash
python3 cron-job-weekly.py --dry-run
```

It changes nothing. It prints how many emails would be labeled and the sender and subject of the first 25 emails that **would be moved to Trash**. Always run this first, and add any important sender you see to `gmail_rules.json`.

### Because of the "no label" rule

- Old emails keep their label. If you move a sender to another category, only their **new** emails get the new label.
- Emails you labeled by hand in Gmail are never trashed by the cleanup.

### Not fixed yet

- `gmail-automation.py` (the first-run script) still labels one email per API call and handles 100 emails per sender. The "100-email limit" section above still applies.
- Nothing checks that a sender is in only one category. Check this yourself in Step 3b.

---

## Files in this folder

| File | What it is |
|---|---|
| `gmail-automation.py` | First-time setup: builds the sender list, labels all existing emails, optionally cleans up |
| `cron-job-weekly.py` | The scheduled job: labels new emails and trashes old unsorted ones (`--dry-run` to preview) |
| `auth.py` | Login code shared by both scripts |
| `token.json` | Your saved login (**private**, created automatically) |
| `client_secret.json` | Your Google key (**private**, never share it) |
| `senders_list.json` | List of everyone who emailed you, with counts (made by the script) |
| `gmail_rules.json` | Your categories and senders (**you write this**) |

## Keeping it up to date

- New people start writing to you? Add their address to a category in `gmail_rules.json`. Until you do, their mail is trashed after 30 days.
- Want to rebuild the sender list? Delete `senders_list.json` and run `python3 gmail-automation.py` again.
- Want a different cleanup age than 30 days? Change `days=30` in the scripts.
- Want to stop everything? Run `crontab -e` and delete the line.

## Troubleshooting

| Problem | What to do |
|---|---|
| `gmail_rules.json not found` | You haven't created the rules file yet (Step 3b). |
| `Expecting property name enclosed in double quotes` or other JSON errors | A JSON file has a typo (missing quote, extra comma, or stray text). Paste it into an online JSON checker to find the line. |
| `insufficient authentication scopes` | The saved login was created with different permissions. Delete `token.json` and run `python3 gmail-automation.py` again to log in. |
| `AUTH FAILED` in the log | Your login expired. Run `python3 gmail-automation.py` by hand once; it creates a new `token.json`. |
| `client_secret.json` crashes or is "not valid JSON" | It was overwritten by an older version of the script. Create a new OAuth client in Google Cloud Console and download the JSON again (Step 2). |
| Browser says "app isn't verified" | Normal for personal projects. Choose **Advanced → Continue**, and make sure your address is listed as a test user. |
| Cron job does nothing | Run `python3 cron-job-weekly.py` by hand and read the error. Check `crontab -l` and the log file. |
| `ModuleNotFoundError` | Install the libraries again: `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client` |
| `client_secret.json not found` | Download the OAuth file from Google Cloud Console (Step 2), rename it to `client_secret.json` and put it in this folder. |
| `Permission denied` when running a script | Run `chmod +x gmail-automation.py cron-job-weekly.py`, or start them with `python3 <file>` as shown above. |
| Cron not running | Look at the log: `cat /tmp/gmail_automation.log`. No file means cron never started; check `sudo systemctl status crond`. |
| `No senders found` | Make sure the mailbox has emails. If `senders_list.json` is empty or broken, delete it and run `python3 gmail-automation.py` again. |
