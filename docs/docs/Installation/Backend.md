# Backend
The backend is an instance of [NocoDB](https://github.com/nocodb/nocodb) and is by default accessible at `<ip-address>:8080`.

The backend is used to manage games visible on the frontend. You can also add users (staff) to the backend, and give them limited access to certain metadata fields.

## Logging in
Visit `<ip-address>:8080` in your browser and login using the default admin credentials; `admin@change.me` and `changeme`.

When you first login, it is advised to change the password for the default user. To do this, click on the menu button in the top right corner, and select `admin@change.me` from the dropdown menu. Then simply change the password.

## Creating a user
To create a user, you'll first need to log in to the admin panel using the default admin user. From there you need to enter the `Games` database, and hit the `Invite Team` button. This will generate a link that you can send to the user you want to invite. You should create your own user first, and then invite other users.

## Defining roles
When you have created a user, you can define what roles they have. `Creator` is the administrator role, and `Editor` is used for users that should be able to edit games, but not necessarily add new ones.

## Adding games
See [[Adding games]] for more information.



