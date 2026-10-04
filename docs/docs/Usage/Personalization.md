# Personalization

Everything below is changed under **Innstillinger** (Settings) in the admin menu. Changes are stored in the database and take effect on the public site as soon as they are saved; no restart or config files are needed. The logo is saved immediately, everything else with **Lagre innstillingene** (Save settings).

## Site

- **Title:** shown in the top left corner and in the browser tab. Leave it empty to use the `TITLE` environment variable.
- **Logo:** shown in the top left corner instead of the gamepad icon, and used as the favicon. Use a square image, such as 256 × 256 pixels (PNG, JPEG, WebP, GIF or ICO, max 2 MB). **Bruk standardikonet** (Use the default icon) removes it again.

## Front page

- **Heading:** the large heading above the game list. Leave it empty to use the site title.
- **Text under the heading:** defaults to "Get your game on". You can use links and simple formatting (`<a href="…">`, `<b>`, `<i>`, `<br>`), for example to link to a form where teachers can request games. Leave it empty to show no text.

## Menu

The menu contains the built-in pages **Spill** (Games), **Installasjon** (Installation) and **Vilkår** (Terms), plus any links you add with **+ Ny lenke** (New link).

- Move items up and down with the arrows. Custom links can be placed anywhere, e.g. `Spill | Installasjon | Request a game | Vilkår | School website`.
- Built-in pages can be renamed (leave the name empty for the default) or hidden by unticking **Vis** (Show).
- Custom links need a name and an address starting with `https://`, `http://`, `mailto:` or `/` (a page on this site). Tick **Ny fane** (New tab) to open the link in a new tab.

## Pages

The installation guide (`/install`) and the terms (`/vilkar`) can be rewritten. Leave a field empty to use the built-in text, or press **Sett inn standardteksten** (Insert the default text) to start from it.

The pages use a small subset of HTML:

| Markup | Result |
| --- | --- |
| `<h1>` and the paragraphs after it | The page heading and introduction |
| `<h2>` | Starts a new card. Add an icon with `<h2 data-icon="windows">` (e.g. `windows`, `mac`, `linux`, `android`, `info`, `shield`, `clock`, `book`, `gamepad`, `help`, `download`, `warning`) |
| `<blockquote>` | A highlighted note |
| `<hr>` | Everything after it is shown as a footnote below the cards |
| `<p>`, `<b>`, `<i>`, `<u>`, `<small>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<a href="…">` | Ordinary text formatting; numbered lists are shown as steps |

Cards are given an anchor from their heading, so a card titled "Windows" can be linked to as `/install#windows`. The game pages' **Hjelp** (Help) links point to `#windows` and `#mac`, and cards named after a platform get a shortcut button at the top of the page.

## Password

See [Restricting access](../Installation/Access.md#logging-in-with-a-password).

Feel free to contribute changes you make to the frontend with a pull request on the [GitHub repository](https://github.com/sondregronas/EduGameDist).
