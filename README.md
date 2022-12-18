<div align="center">

# 🕹️ Game Distribution for Schools 🏫
[![GitHub Pages](https://badgen.net/badge/demo/github%20pages/?icon=chrome)](https://sondregronas.github.io/EduGameDist/)
[![GitHub Pages](https://badgen.net/badge/docs/github%20pages/?icon=chrome)](https://sondregronas.github.io/EduGameDist/docs)
[![Build Status](https://img.shields.io/github/actions/workflow/status/sondregronas/EduGameDist/CI.yml?branch=main)](https://github.com/sondregronas/EduGameDist/)
[![GitHub latest commit](https://img.shields.io/github/last-commit/sondregronas/EduGameDist)](https://github.com/sondregronas/EduGameDist/commit/)

Simple game distribution for schools. Dockerized and ready to deploy.

![Frontend Preview](.github/media/preview.webp)

</div>

> **Note:** Parts of this project is in Norwegian, as it was made for a Norwegian school, you may need to modify all `.pug` files in the `views` folder by uncommenting the volume mount in the `docker-compose.yml` file. This will allow you to edit the files directly on your host machine, and the changes will be reflected in the container.

## Disclaimer
While this project allows for managing distribution of games or any files over the internet, it's only intended for local and internal use. Take additional precautions to ensure the service is only accessible to those eligible by law in your area. Deploy at your own risk.

## Installation
Please refer to the [documentation](https://sondregronas.github.io/EduGameDist/docs) on [how to install](https://sondregronas.github.io/EduGameDist/docs/Installation/docker/) and [use](https://sondregronas.github.io/EduGameDist/docs/Usage/Adding-games/) this project.

## Educator friendly NocoDB Backend
The backend is powered by [NocoDB](https://nocodb.com/), a simple and easy to use database management tool.

![Backend Preview](.github/media/preview_db.webp)

## Contributing
Refer to [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
