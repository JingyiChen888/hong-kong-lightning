# Process

This repository was developed with help from ChatGPT. I described the phenomenon
and provided the Hong Kong Observatory data source. ChatGPT helped me understand
the file and drafted the first versions of `fetch.py`, `plot.py`, `animate.py` and
the README. I ran the scripts locally, looked at the generated pictures and asked
for changes when the result was unclear or did not look right.

**One thing I kept, and why.** I kept the `complete_years()` check in the plotting
script. At first, I wondered why the picture stopped at 2025 even though the file
contained 2026 data. After checking the file, I found that 2026 ended in August.
Including it as a complete calendar would make September to December look like
zero-lightning months. The function keeps the raw file unchanged but excludes
incomplete years from the picture.

**One thing I rejected, and why.** The first picture was a rectangular heatmap. It
was readable, but it looked more like a table or a system log than a natural
phenomenon. I asked for a circular version because a year repeats as a cycle. I
kept the heatmap in `out/` as a record of the first analytical version, but did not
use it as the main picture.

I also considered a Hong Kong map, but rejected it because the source contains only
one total for the whole territory each day and no locations for individual
strikes. I revised the first README draft as well, separating what the pictures
show from what they hide and changing wording that did not sound natural to me.
