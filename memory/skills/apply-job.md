---
name: apply-job
autonomy: supervised
demonstrations: 0
runs: 0
clean_runs_in_a_row: 0
updated: 2026-10-04 00:00
---
# Apply to a job

## Goal
For each chosen job posting, get a tailored resume from the user's Claude "Resume agent" chat,
fill the application form with it, get the open-ended answers from the same chat, and submit
after the user says yes.

## When to use / inputs
The user names a careers page (e.g. Anthropic careers) and which jobs to apply to ("the first 3
new ones", or a list of titles/URLs). Skip jobs already listed in the "Applied" section of the
run logs unless told otherwise.

## Apps and places
- Browser tab A: the company careers page / job posting / application form.
- Browser tab B: claude.ai, chat session "Resume agent" (find it in the sidebar by name).
- Downloads folder: where the tailored resume lands after downloading it from Claude.

## Steps
For each job:
1. In tab A, open the job posting. Select the full job description (title, team, responsibilities,
   requirements) and copy it (ctrl/cmd+A inside the description is too much; drag-select or use the
   description container).
2. Switch to tab B, the "Resume agent" chat. Paste the job description and send it. Wait until
   Claude has finished responding (the stop button disappears).
3. Download the tailored resume Claude produced (download button on the file card). Note the file
   name; it lands in Downloads.
4. Switch back to tab A and click "Apply". Upload the downloaded resume in the resume/CV field.
5. Fill standard fields (name, email, phone, location, LinkedIn, website) from profile.md.
6. For each open-ended question (e.g. "Why do you want to work at Anthropic?"): copy the question,
   go to tab B, paste it into the same chat with "Answer this for the application above, under N
   words" and send; copy Claude's answer; return to tab A and paste it into the field.
7. Scroll through the whole form, check every required field (marked *) is filled, and zoom to
   read anything unclear.
8. confirm_with_human with the job title and a summary of every answer, then click Submit.
9. Wait for the confirmation page and note "Applied: <title> (<date>)" in the summary.

## Decision rules
- Contact/basic fields: from profile.md.
- Open-ended "why us / why this role / tell us about" questions: from the Resume agent chat.
- Work authorization, sponsorship, relocation, salary expectations, start date, demographic /
  EEO / disability / veteran questions: ALWAYS ask the user unless profile.md has an explicit
  answer for exactly that question.
- If the form needs an account login, hand_over_to_human.

## Ask the human
- Any required field with no source above.
- Whether to apply when the role looks like a poor fit with the profile.

## Confirm before
- Clicking Submit / Send application.
- Accepting any terms, privacy notices, or AI-use attestations.

## Pitfalls
- The Claude response may still be streaming; wait before copying or downloading.
- Make sure the uploaded resume is the one for THIS job (check the file name / time).
- Some forms parse the resume and overwrite fields; re-check the fields after uploading.

## Change log
- 2026-10-04: Seeded from the user's description of their morning workflow. Will be rewritten after
  the first `watch` demonstration.
