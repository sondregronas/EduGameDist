# Personalization

Everything below is changed under **Innstillinger** (Settings) in the admin menu. Changes are stored in the database and take effect on the public site as soon as they are saved; no restart or config files are needed. The logo is saved immediately, everything else with **Lagre innstillingene** (Save settings).

## Site

- **Title:** shown in the top left corner and in the browser tab. Leave it empty to use the `TITLE` environment variable.
- **Logo:** shown in the top left corner instead of the gamepad icon, and used as the favicon. Use a square image, such as 256 × 256 pixels (PNG, JPEG, WebP, GIF or ICO, max 2 MB). **Bruk standardikonet** (Use the default icon) removes it again.

## Front page

- **Heading:** the large heading above the game list. Leave it empty to use the site title.
- **Text under the heading:** defaults to "Get your game on". Line breaks are kept as you type them, and you can use links and simple formatting (`<a href="…">`, `<b>`, `<i>`), for example to link to a form where teachers can request games. Leave it empty to show no text.

## Menu

The menu contains the built-in pages **Spill** (Games), **Installasjon** (Installation) and **Vilkår** (Terms), plus any links you add with **+ Ny lenke** (New link).

- Move items up and down with the arrows. Custom links can be placed anywhere, e.g. `Spill | Installasjon | Request a game | Vilkår | School website`.
- Built-in pages can be renamed (leave the name empty for the default) or hidden by unticking **Vis** (Show).
- Custom links need a name and an address starting with `https://`, `http://`, `mailto:` or `/` (a page on this site). Tick **Ny fane** (New tab) to open the link in a new tab.
- Click a custom link's icon to cycle through the available icons (link, home, school, form, e-mail, calendar, star and more).

## Pages

The installation guide (`/install`) and the terms (`/vilkar`) can be rewritten. Leave a field empty to use the built-in text, or press **Sett inn standardteksten** (Insert the default text) to start from it.

The pages use a small subset of HTML. Line breaks in the text are kept, so plain paragraphs need no tags:

| Markup | Result |
| --- | --- |
| `<h1>` and the paragraphs after it | The page heading and introduction |
| `<h2>` | Starts a new card. Add an icon with `<h2 data-icon="windows">` (e.g. `windows`, `mac`, `linux`, `android`, `info`, `shield`, `clock`, `book`, `gamepad`, `help`, `download`, `warning`) |
| `<blockquote>` | A highlighted note |
| `<hr>` | Everything after it is shown as a footnote below the cards |
| `<p>`, `<b>`, `<i>`, `<u>`, `<small>`, `<ul>`, `<ol>`, `<li>`, `<a href="…">` | Ordinary text formatting; numbered lists are shown as steps |

Cards are given an anchor from their heading, so a card titled "Windows" can be linked to as `/install#windows`. The game pages' **Hjelp** (Help) links point to `#windows` and `#mac`, and cards named after a platform get a shortcut button at the top of the page.

## Categories

The **Kategorier** (Categories) section is the shared list of categories that games pick from. The same list opens from the **Kategorier** button above the game list on the admin front page. Changes are saved immediately:

- Add a category with the field below the list. New categories are added at the end.
- Rename a category by editing its name. Every game with that category shows the new name, since the games point at the category itself.
- Delete a category with the bin icon. It is removed from all games that had it.
- Change the order by dragging the handle on the left, or by focusing it and using the arrow keys. **Sorter alfabetisk** (Sort alphabetically) puts the list in A–Z order. The category filter on the front page uses this order.

The list also shows how many games use each category. Categories can also be created from a game page; see [Adding games](Adding-games.md#game-information).

## Light and dark mode

Visitors can switch between dark and light mode with the switch at the top right, and the choice is remembered in their browser. Until they choose, the site follows their system setting: light when the device is set to light mode, otherwise dark. The colours are CSS variables at the top of `src/public/css/app.css`; light mode only overrides those.

## Password

See [Restricting access](../Installation/Access.md#logging-in-with-a-password).

Feel free to contribute changes you make to the frontend with a pull request on the [GitHub repository](https://github.com/sondregronas/EduGameDist).
