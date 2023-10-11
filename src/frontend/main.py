"""Primary frontend module."""

import flask

import backend.games as games


def create_app():
    app = flask.Flask(__name__)

    @app.route("/")
    def get_index() -> str:
        return flask.render_template('index.html')

    @app.route("/games")
    def get_games() -> str:
        return flask.render_template('games.html', games=games.get_all())

    @app.route("/games/<game_id>")
    def get_game(game_id) -> str:
        return flask.render_template('game.html', game=games.get(game_id))

    @app.route("/login")
    def get_login() -> str:
        return flask.render_template('login.html')

    @app.route("/logout")
    def get_logout() -> flask.Response:
        flask.session.clear()
        return flask.redirect(flask.url_for('get_index'))

    return app
