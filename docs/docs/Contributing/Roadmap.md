# Roadmap
On this page you can find the current roadmap of the project. The roadmap is a living document and will be updated as needed.

Some goals might be a bit too ambitious or not feasible. If you have any suggestions, feel free to open an issue or pull request.

## UI-Redesign
The current UI is a bit of a mess and old-fashioned. It is also not very mobile friendly (not that it is a priority, but it would be nice to have). I will attempt to re-design the frontend using [Tailwind](https://tailwindcss.com/) when I feel more comfortable with it. Alternatively a different framework might be worth looking into, like Svelte or React.

## Backend
The integrated admin application now provides a teacher-friendly way to manage games. Future work may improve roles and collaborative editing; access to the admin app is currently controlled by the deployment's Nginx Proxy Manager configuration.

## Metadata scraping
An integration with something like https://thegamesdb.net/ for example would be nice, where you can watch a games' folder, or select games from a list, and it will automatically add the game and relevant metadata to the database. (Potentially via https://github.com/Sude-/lgogdownloader)

## Custom download experience
Currently, the download experience is very basic; a single download button that downloads a single file. Most games fit for game-based learning are small enough to justify a single download button, but some games are quite large, or simply contain multiple files (such as DLC). A solution would probably either require reworking the download button to open a modal, or by switching to a desktop app.

## Authentication and access management for teachers
Currently, the service is running as a web server without any authentication. This is mostly fine, but it would be nice to authenticate users for remote access and potentially limit access to certain games for certain users (for example, only allow students to access games that are assigned to them). However, there are pros and cons to either approach, and it might be problematic to implement, so this is not a priority.
