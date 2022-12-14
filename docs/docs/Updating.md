# Updating
To update your docker instance, you can use the following commands:
```bash
docker-compose pull
docker-compose up -d
```

Alternatively you can use something like Watchtower to automatically update your containers.

## New database features
Currently, there is no simple way of updating your instance in case of database changes, so adding additional features must be done manually. Be sure to create a backup of both `noco.db.defaults` and `gamedb.db` before updating.

I intend to tackle this later, but for now the database columns in `gamedb.db` will not change, so worst case you'll lose out on new features when and if they are added.