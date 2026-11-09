# jnrachele.com

Personal website of Dr Jerome N Rachele, hosted free on GitHub Pages.

## Updating the site

The quickest way: ask Claude to add a publication, grant, report or media item. Claude edits the content and sends back updated files.

To do it yourself:
- **Small text change:** open the `.html` file on GitHub, click the pencil icon, edit, then click **Commit changes**. The live site updates in about a minute.
- **Add a publication:** edit `_source/publications.txt` (one line per paper, newest first). Then run `python3 build.py ..` from the `_source` folder, which rebuilds every page. Put the PDF in `files/papers/`.
- Grants, reports, media and your profile details live in `_source/site_data.py`.

## Files

- `index.html`, `academic-publications.html`, `grants.html`, `reports.html`, `media.html`: the pages
- `styles.css`: the look of every page
- `files/`: PDFs, the SEIFA data and your photo, copied from Wix by the **Copy files from Wix** workflow (Actions tab)
- `CNAME`: tells GitHub Pages to serve the site at jnrachele.com
- `_source/`: the content and the generator (GitHub Pages doesn't publish folders whose names start with `_`)

## DNS (at GoDaddy)

| Type  | Name | Value                    |
|-------|------|--------------------------|
| A     | @    | 185.199.108.153          |
| A     | @    | 185.199.109.153          |
| A     | @    | 185.199.110.153          |
| A     | @    | 185.199.111.153          |
| CNAME | www  | YOUR-USERNAME.github.io  |
