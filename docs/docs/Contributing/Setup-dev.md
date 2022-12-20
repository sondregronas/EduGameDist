# Setup for development
Here's a quick, temporary guide to get started with development. You'll need to have NodeJS installed on your system.

1. Clone the repository
2. Run `npm install` to install dependencies
3. Run `npm run dev` to start the development server
4. Navigate to `localhost:80` to view the frontend, it should automatically open in your browser and reload on changes

Currently, the backend is not included in the development server. You will need to run the backend separately, any database viewer should work. I will attempt to generate a mock database in the future.

Alternatively you can create a dev environment by running the `docker-compose.yml` file and mounting the `/app` folder to the `src` directory.