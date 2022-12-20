# Configuring the frontend
Inside the `docker-compose.yml` file, you can configure the title of the website by changing the `TITLE` environment variable. 

You can also configure the port that the frontend is exposed on by changing the `ports` section. The default port is `80`.

## Adding games
All games are managed by the backend, once added to the backend, they will be available on the frontend (within 15 minutes).

See [[Adding games]] for more information.

## Personalization
The frontend can be personalized by changing the files in the `cfg` folder. The `cfg` folder is mounted to the frontend container, so any changes you make to the files will be reflected on the frontend.

> [!NOTE]+
> Updating config may require a restart of the frontend container.
> To restart the frontend container, run `docker-compose restart` in the folder where the `docker-compose.yml` file is located.
