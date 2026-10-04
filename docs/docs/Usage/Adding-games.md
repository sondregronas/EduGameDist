# Adding games

Open the admin app at the address configured in Nginx Proxy Manager. Choose **Legg til spill** (Add game) on the front page, enter a Steam link, app ID or game name and press **Hent fra Steam** (Fetch from Steam), then choose **Opprett og legg til filer** (Create and add files). The game opens in edit mode and appears on the public site straight away.

## Fetching information from Steam

The title, short description, cover image, developer and Steam link are filled in when Steam has them. The cover image is downloaded and stored on the server. The app also looks for the game on GOG, itch.io and Humble Bundle and adds links for exact matches (Humble is best effort). Check and edit the fields before saving.

## Game information

- **Title** and **description** are shown in the overview and on the game page.
- **Teacher note** is shown on the game page. You can use simple HTML: `<a href="https://…">link</a>`, `<br>`, `<p>`, `<b>`, `<i>`, `<u>`, `<ul>`, `<ol>` and `<li>`. Everything else is removed. Ordinary line breaks are kept.
- **Cover image** can be fetched from Steam, given as a URL or uploaded.
- **Number of players**, **play time**, **developer** and **developer website** are optional.
- **Categories** are added with **+ Ny kategori** (New category) and removed with the minus button on each category. Visitors can filter the front page by category.
- **Store links** are added with **+ Ny lenke** (New link); the store is recognized from the address.
- **Browser game link** is used when the game can be started directly in the browser.

Categories and store links are stored as separate, ordered records linked to the game, not as fixed `Category1`/`Store1` columns.

## Uploading files

Press **Rediger** (Edit) on the game page and drop files on the area for the right platform (or click the area to choose files). Repeat to add more files to the same platform or files for another platform. Existing files can be removed in edit mode.

Each file is sent in one streamed request and stored unchanged under its own name in `./games/<Platform>/<game>/` on the server, for example `./games/Windows/oslo-2084/Oslo2084-Setup.zip`. Characters that are not allowed in file names are replaced with `_`, and if a file with the same name already exists, the new one gets a number, like `Setup (2).zip`. Visitors always download the file under the name it was uploaded with.

The app has no size limit, so files of more than 20 GB can be uploaded, but an upload cannot be resumed if it is interrupted, and the page must stay open until it finishes. The proxy must allow large requests (`client_max_body_size 0`). See [Docker installation](../Installation/docker.md) for the NPM configuration.

## Licenses and distribution

Make sure you have the right to distribute the games. See [Acquiring games](Acquiring-games.md) and the project's [terms](Terms-and-Conditions.md).
