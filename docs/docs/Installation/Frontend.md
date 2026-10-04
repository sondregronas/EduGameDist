# Frontend

The frontend is the public, read-only website. Its port is set in the service's `ports` section in `docker-compose.yml`; the default is port `80`.

## Adding games

Games are managed in the separate admin app, and changes are published on the frontend as soon as they are saved. See [Adding games](../Usage/Adding-games.md).

## Customization

The title, logo (favicon), front page heading and text, menu links, installation guide and terms are changed under **Innstillinger** (Settings) in admin, and take effect immediately without a restart. See [Personalization](../Usage/Personalization.md).

Visitors can filter the game list by category and platform. Filtered views can be linked to directly, for example `/?category=puzzle&platform=windows`, and the categories on a game's page link to the matching filter.
