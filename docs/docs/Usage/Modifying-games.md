# Modifying games
The backend provides by default 2 different views for modifying games. You're free to add more views if you want to, but the default views should be enough for most use cases.

The first view is the `Games` table, which provides a traditional table view of the games. This view is useful for quickly editing a game, but it's not very user-friendly.

The second view is the `Friendly` view, which provides a card view of the games. This view is more user-friendly, but has fewer features than the `Games` table.

## Games table
Supports search, sorting, pagination, and filtering. You can also add new games from this view, but it's not very user-friendly. Use this view to make adjustments to existing games that are already in the database.

## Friendly view
Provides a card view of the games. This view is more user-friendly, but has limited editing capabilities, perfect for teachers that don't want to mess with the database.

By default, this view contains the following fields:
- [ ] **Title**
- [ ] **Note**
- [ ] **Cover**
- [ ] **Time**
- [ ] **Players**
- [ ] **Category**

The reason for this is that the other fields normally shouldn't require any editing.

## New entry
A form for adding new games.

See [[Adding games]] for more information.