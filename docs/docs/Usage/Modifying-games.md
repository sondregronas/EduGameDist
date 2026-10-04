# Modifying games

Open the admin app via Nginx Proxy Manager and choose a game. The page looks like the public one, but has a **Rediger** (Edit) button. In edit mode you change text, categories and links directly on the page. Press **Lagre** (Save) to publish; the public site picks up the new values immediately.

You can change all metadata fields, add or remove categories and store links, update the Steam information (**Hent fra Steam**), find store links automatically (**Finn butikklenker**), and upload or remove files for each platform. There is no fixed limit of three categories, five store links or one file per platform.

Renaming a game changes its address, and its folders in `./games/<Platform>/` are renamed to match.

Categories can be added, removed and reordered straight from the game page, without pressing **Rediger**; those changes are saved immediately. In edit mode they are saved together with everything else when you press **Lagre**.

## Hiding games

A game can be hidden from visitors without deleting it, for example while you are still adding files:

- On the admin front page, click the **eye icon** on the game's cover. Hidden games are shown blurred with a **Skjult** (Hidden) badge.
- On the game page, use the **Synlig / Skjult** (Visible / Hidden) button next to **Rediger**.

Hidden games are left out of the public game list, and their page and files return "not found" on the public site. Everything stays available in admin, and you can show the game again with the same button.

## Deleting

When you delete a game, the files uploaded for it are deleted too, along with its folders in `./games/<Platform>/`. Files from very old versions that could not be found when the app started (and therefore were not moved into a game folder) are left alone on disk.
