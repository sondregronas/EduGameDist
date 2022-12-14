# Contributing
Improvements are very welcome, feel free to open a pull request or issue. The CSS and Frontend in general is a bit of a mess, so feel free to improve it. Design is not my strong suit.

Keep in mind this project is aimed at schools, so it should be easy to use and understand. It is also aimed at being used by teachers, so it should be easy to maintain. Performance or fancy features are not a priority, simplicity is.

## Development
The project is built on Node.js, and uses Express for the backend and Pug for the frontend. The database is SQLite, and for now is managed using NocoDB (which is a web-based database manager). The reason for this is that it is easy to use, and it is relatively easy for anyone to manage the database using the web interface.

### Setup
Here's a quick guide to get started with development. This assumes you have a basic understanding of how to use the command line.

1. Clone the repository
2. Run `npm install` to install dependencies
3. Run `npm run dev` to start the development server
4. Navigate to `localhost:80` to view the frontend, it should automatically open in your browser and reload on changes
5. Currently, the backend is not included in the development server. You will need to run the backend separately, any database viewer should work, but adding cover art manually might be tricky. I will attempt to generate a mock database in the future

You can alternatively install everything using `docker-compose.yml` and exposing the `/app` folder to your host machine. This will allow you to edit the files directly on your host machine, and the changes will be reflected in the container.

You can also clone the `gh-pages` branch to view the frontend without the backend, which can be used if you just want to modify the CSS or javascript files.

## How to contribute
Feel free to contribute in any way you see fit. If you have questions, suggestions or ideas, please open an issue.

Don't be afraid to fork the project or open a pull request, even if it's just a small change. I'll be happy to review it. If you're unsure about something, feel free to ask.

You can also contribute by reporting bugs, suggesting new features or monetarily by sponsoring the project.